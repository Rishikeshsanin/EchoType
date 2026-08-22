from __future__ import annotations

import collections
import unicodedata

import numpy as np
import torch

NEUTRAL = "NEUTRAL"
SCRIPT_COMPANIONS = {
    "LATIN": {"LATIN"},
    "DEVANAGARI": {"DEVANAGARI"},
    "BENGALI": {"BENGALI"},
    "KANNADA": {"KANNADA"},
    "TELUGU": {"TELUGU"},
    "TAMIL": {"TAMIL"},
    "MALAYALAM": {"MALAYALAM"},
    "GUJARATI": {"GUJARATI"},
    "GURMUKHI": {"GURMUKHI"},
    "ORIYA": {"ORIYA"},
    "OL": {"OL"},
    "MEETEI": {"MEETEI", "BENGALI"},
}


def piece_script(piece: str) -> str:
    counts: collections.Counter[str] = collections.Counter()
    for char in piece:
        if not char.isalpha():
            continue
        try:
            counts[unicodedata.name(char).split(" ")[0]] += 1
        except ValueError:
            continue
    return counts.most_common(1)[0][0] if counts else NEUTRAL


class ScriptMasker:
    def __init__(self, sentencepiece, vocab_size: int, blank_id: int, device) -> None:
        self.sp = sentencepiece
        self.vocab_size = int(vocab_size)
        self.blank_id = int(blank_id)
        self.device = device
        self._scripts = [piece_script(sentencepiece.id_to_piece(i)) for i in range(self.vocab_size)]
        self._cache: dict[str, torch.Tensor] = {}

    def available_scripts(self) -> set[str]:
        return set(self._scripts) - {NEUTRAL}

    def mask_for(self, script: str | None) -> torch.Tensor | None:
        if script is None:
            return None
        if script in self._cache:
            return self._cache[script]

        allowed = SCRIPT_COMPANIONS.get(script, {script})
        size = self.blank_id + 1
        mask = torch.zeros(size, dtype=torch.bool, device=self.device)
        for index, token_script in enumerate(self._scripts):
            if token_script == NEUTRAL or token_script in allowed:
                mask[index] = True
        mask[self.blank_id] = True
        self._cache[script] = mask
        return mask


@torch.no_grad()
def greedy_decode(model, enc_out, total_frames: int, mask=None, *, score: bool = False):
    config = model.config
    device = model._anchor.device
    num_durations = config.num_durations
    blank_id = config.blank_id
    durations = config.durations
    dtype = model._io_dtype

    hidden = torch.zeros(
        config.pred_rnn_layers,
        1,
        config.pred_hidden,
        device=device,
        dtype=dtype,
    )
    cell = torch.zeros_like(hidden)
    last_token = blank_id
    tokens: list[int] = []
    frames: list[int] = []
    target_length = torch.ones(1, dtype=torch.int32, device=device)
    total_logprob = 0.0
    steps = 0
    frame_index = 0

    while frame_index < total_frames:
        frame = enc_out.narrow(2, frame_index, 1)
        added = 0
        needs_symbol = True
        while needs_symbol and added < config.max_symbols:
            target = torch.tensor([[last_token]], dtype=torch.int32, device=device)
            logits, _, hidden_next, cell_next = model.decoder_joint(
                frame,
                target,
                target_length,
                hidden,
                cell,
            )
            logits = logits[0, 0, 0]
            token_logits = logits[:-num_durations]
            if mask is not None:
                token_logits = token_logits.masked_fill(~mask, float("-inf"))

            token = int(token_logits.argmax().item())
            skip = durations[int(logits[-num_durations:].argmax().item())]
            if score:
                logprob = torch.log_softmax(logits[:-num_durations].float(), dim=-1)[token]
                total_logprob += float(logprob)
                steps += 1

            if token != blank_id:
                tokens.append(token)
                frames.append(frame_index)
                hidden, cell, last_token = hidden_next, cell_next, token

            added += 1
            frame_index += skip
            needs_symbol = skip == 0

        if added == config.max_symbols:
            frame_index += 1

    if score:
        return tokens, frames, {
            "total_logprob": total_logprob,
            "steps": steps,
            "frames": total_frames,
            "tokens": len(tokens),
        }
    return tokens, frames


@torch.no_grad()
def transcribe(model, waveform, masker: ScriptMasker | None = None, script: str | None = None, *, timestamps: bool = True):
    device = model._anchor.device
    model._ensure_loaded()
    tokenizer = model._get_tokenizer()

    wave_tensor = torch.as_tensor(
        np.ascontiguousarray(waveform, dtype=np.float32)
    ).reshape(-1)
    features, feature_length = model.extract_features(
        wave_tensor.unsqueeze(0),
        torch.tensor([wave_tensor.shape[0]]),
    )
    encoded, encoded_length = model.encoder(
        features.to(model._io_dtype),
        feature_length.to(device),
    )
    total_frames = int(encoded_length[0].item())

    mask = masker.mask_for(script) if masker is not None and script else None
    tokens, frames = greedy_decode(model, encoded[0:1], total_frames, mask=mask)
    text = tokenizer.decode([int(token) for token in tokens])
    result = {"text": text, "tokens": tokens, "frames": frames, "timestamp": None}

    if timestamps and tokens:
        subsampling = int(getattr(model.config, "subsampling_factor", 8))
        frame_duration = model._frame_seconds()
        total = -(-int(feature_length[0].item()) // subsampling)
        try:
            result["timestamp"] = model._make_timestamps(
                tokenizer,
                tokens,
                frames,
                frame_duration,
                total,
            )
        except Exception:
            result["timestamp"] = None
    return result


SHORT_UTTERANCE_SECONDS = 4.0
MIN_TOKENS_FOR_TRUST = 3


def dominant_script(text: str) -> str | None:
    counts: collections.Counter[str] = collections.Counter()
    for char in text or "":
        if not char.isalpha():
            continue
        try:
            counts[unicodedata.name(char).split(" ")[0]] += 1
        except ValueError:
            continue
    return counts.most_common(1)[0][0] if counts else None


class LanguageTracker:
    """Sticky session-script prior for acoustically ambiguous short utterances."""

    def __init__(self, switch_evidence: int = 2) -> None:
        self.switch_evidence = switch_evidence
        self._session: str | None = None
        self._pending: str | None = None
        self._pending_hits = 0

    def reset(self) -> None:
        self._session = None
        self._pending = None
        self._pending_hits = 0

    @property
    def session_script(self) -> str | None:
        return self._session

    def prior_for(self, seconds: float) -> str | None:
        return None if seconds >= SHORT_UTTERANCE_SECONDS else self._session

    def observe(self, script: str | None, seconds: float, tokens: int) -> str | None:
        del seconds
        if not script or tokens < MIN_TOKENS_FOR_TRUST:
            return self._session
        if self._session is None:
            self._session = script
            self._pending = None
            self._pending_hits = 0
            return script
        if script == self._session:
            self._pending = None
            self._pending_hits = 0
            return script

        if self._pending == script:
            self._pending_hits += 1
        else:
            self._pending = script
            self._pending_hits = 1

        if self._pending_hits >= self.switch_evidence:
            self._session = script
            self._pending = None
            self._pending_hits = 0
            return script
        return self._session


class Hypothesis:
    def __init__(self, text: str, timestamp=None) -> None:
        self.text = text
        self.timestamp = timestamp
        self.y_sequence = []

from __future__ import annotations

import os
import queue
import threading
import time
import traceback
from dataclasses import dataclass

import numpy as np

from echotype.core import decoding
from echotype.core.audio import SAMPLE_RATE
from echotype.core.cleanup import SMART, clean_hypothesis, word_count
from echotype.core.languages import AUTO, script_for_code
from echotype.services.model_revision import resolve_persisted_revision

MODEL_REPO = "SharadhNaiduTrains/sravaani-flow-model"
UPSTREAM_REPO = "ARTPARK-IISc/SraVaani-1.0"
MODEL_REPOS = (MODEL_REPO, UPSTREAM_REPO)

IDLE = "idle"
LOADING = "loading"
READY = "ready"
BUSY = "busy"
FAILED = "failed"


@dataclass(slots=True)
class Job:
    audio: np.ndarray
    info: dict
    target: object | None = None
    mode: str = SMART
    tag: str = ""
    created: float = 0.0

    def __post_init__(self) -> None:
        if not self.created:
            self.created = time.time()


@dataclass(slots=True)
class Result:
    text: str
    raw: str
    job: Job
    elapsed: float
    error: str | None = None
    changed_by_cleanup: bool = False

    @property
    def words(self) -> int:
        return word_count(self.text or "")

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.text)


def cuda_usable() -> bool:
    try:
        import torch

        if not torch.cuda.is_available() or torch.cuda.device_count() < 1:
            return False
        torch.cuda.get_device_name(0)
        torch.zeros(1).cuda()
        return True
    except Exception:
        return False


def resolve_token() -> str | None:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    return token.strip() if token else None


def _resolve_revision(repo: str, settings) -> str | None:
    """Resolve and persist an immutable mirror revision for this installation.

    This is an improvement over V1, which always trusted whatever was at the
    remote repo's moving HEAD. Release builds will eventually hard-pin the SHA
    in source as well; during development we resolve it once and persist it.
    """
    try:
        from huggingface_hub import model_info
    except Exception:
        return None
    return resolve_persisted_revision(
        repo,
        settings,
        pinned_repo=MODEL_REPO,
        model_info=model_info,
    )


class TranscriptionEngine:
    MIN_SPEECH_RATIO = 0.06
    MIN_SECONDS = 0.25
    JUNK_TOKENS = {
        "um",
        "uh",
        "hmm",
        "mm",
        "hm",
        "ah",
        "eh",
        "oh",
        "हूँ",
        "हूं",
        "उम",
        "উম",
        "ಉಮ್",
        "ఉమ్",
        "अं",
        "ಅಂ",
    }

    def __init__(self, settings, on_status=None, on_result=None) -> None:
        self.settings = settings
        self.on_status = on_status or (lambda *_args: None)
        self.on_result = on_result or (lambda _result: None)
        self.status = IDLE
        self.detail = ""
        self.device = "cpu"
        self.precision = "fp32"
        self.model = None
        self.model_repo = ""
        self.model_revision: str | None = None
        self.load_seconds = 0.0
        self.last_rtf = 0.0
        self._queue: queue.Queue[Job | None] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._masker: decoding.ScriptMasker | None = None
        self._tracker = decoding.LanguageTracker()
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def _set_status(self, status: str, detail: str = "") -> None:
        self.status = status
        self.detail = detail
        try:
            self.on_status(status, detail)
        except Exception:
            pass

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._stop.clear()
        self._worker = threading.Thread(target=self._run, name="echotype-asr", daemon=True)
        self._worker.start()

    def shutdown(self) -> None:
        self._stop.set()
        self._queue.put(None)

    def submit(self, audio, info, *, target=None, mode: str = SMART, tag: str = "") -> None:
        self._queue.put(Job(audio=audio, info=info or {}, target=target, mode=mode, tag=tag))

    @property
    def pending(self) -> int:
        return self._queue.qsize()

    def _pick_device(self) -> str:
        requested = str(self.settings.get("device", "auto")).lower()
        if requested == "cpu":
            return "cpu"
        if cuda_usable():
            return "cuda"
        if requested == "cuda":
            self._set_status(LOADING, "CUDA requested but unavailable; using CPU")
        return "cpu"

    def _load(self) -> None:
        import torch
        from transformers import AutoModel

        token = resolve_token()
        device = self._pick_device()
        wants_fp16 = (
            str(self.settings.get("precision", "fp16")).lower() == "fp16"
            and device == "cuda"
        )
        dtype = torch.float16 if wants_fp16 else torch.float32

        self._set_status(LOADING, f"Loading speech model on {device.upper()}")
        started = time.time()
        model = None
        last_error: Exception | None = None

        for repo in MODEL_REPOS:
            revision = _resolve_revision(repo, self.settings)
            kwargs = {
                "trust_remote_code": True,
                "dtype": dtype,
            }
            if revision:
                kwargs["revision"] = revision
            if token and repo == UPSTREAM_REPO:
                kwargs["token"] = token

            try:
                model = AutoModel.from_pretrained(repo, **kwargs)
            except TypeError:
                # Compatibility with Transformers versions that still use
                # torch_dtype instead of dtype.
                kwargs.pop("dtype", None)
                kwargs["torch_dtype"] = dtype
                try:
                    model = AutoModel.from_pretrained(repo, **kwargs)
                except Exception as exc:
                    last_error = exc
            except Exception as exc:
                last_error = exc

            if model is not None:
                self.model_repo = repo
                self.model_revision = revision
                break

        if model is None:
            raise last_error or RuntimeError("Could not load SraVaani model")

        model = model.to(device).eval()

        # Warm up the model and verify that the selected device really works.
        try:
            model.transcribe([np.zeros(SAMPLE_RATE, dtype=np.float32)])
        except Exception:
            if device != "cuda":
                raise
            device = "cpu"
            wants_fp16 = False
            model = model.float().to("cpu").eval()
            model.transcribe([np.zeros(SAMPLE_RATE, dtype=np.float32)])

        try:
            tokenizer = model._get_tokenizer()
            self._masker = decoding.ScriptMasker(
                tokenizer,
                model.config.vocab_size,
                model.config.blank_id,
                model._anchor.device,
            )
        except Exception:
            self._masker = None

        self.model = model
        self.device = device
        self.precision = "fp16" if wants_fp16 else "fp32"
        self.load_seconds = time.time() - started
        self._set_status(READY, f"{device.upper()} / {self.precision}")

    def _run(self) -> None:
        try:
            self._load()
        except Exception as exc:
            self._set_status(FAILED, self._explain(exc))
            traceback.print_exc()
            return

        while not self._stop.is_set():
            job = self._queue.get()
            if job is None:
                break
            try:
                self._handle(job)
            except Exception as exc:
                traceback.print_exc()
                self._emit(Result("", "", job, 0.0, error=str(exc)))
            finally:
                if self.status != FAILED:
                    self._set_status(READY, f"{self.device.upper()} / {self.precision}")

    @staticmethod
    def _explain(exc: Exception) -> str:
        text = str(exc)
        lower = text.lower()
        if "401" in text or "403" in text or "gated" in lower or "authoriz" in lower:
            return "Speech model download was refused. Check model access or network settings."
        if "connect" in lower or "resolve" in lower or "network" in lower or "timeout" in lower:
            return "Network unavailable and the speech model is not cached yet."
        if "out of memory" in lower:
            return "GPU out of memory. Switch EchoType compute to CPU."
        return text[:220]

    def _emit(self, result: Result) -> None:
        try:
            self.on_result(result)
        except Exception:
            traceback.print_exc()

    def _handle(self, job: Job) -> None:
        audio = job.audio
        seconds = audio.size / float(SAMPLE_RATE) if audio is not None else 0.0
        if audio is None or seconds < self.MIN_SECONDS:
            self._emit(Result("", "", job, 0.0, error="too_short"))
            return
        if float(job.info.get("speech_ratio", 1.0)) < self.MIN_SPEECH_RATIO:
            self._emit(Result("", "", job, 0.0, error="no_speech"))
            return

        with self._lock:
            self._set_status(BUSY, f"Transcribing {seconds:.1f}s")
            started = time.time()
            hypothesis = self._transcribe(audio)
            elapsed = time.time() - started

        self.last_rtf = elapsed / max(seconds, 1e-6)
        raw = getattr(hypothesis, "text", "") or ""
        if self._is_junk(raw, seconds):
            self._emit(Result("", raw, job, elapsed, error="no_speech"))
            return

        cleaned = clean_hypothesis(
            hypothesis,
            mode=job.mode,
            spoken_punctuation=bool(self.settings.get("spoken_punctuation", True)),
            vocabulary=self.settings.get("vocabulary"),
            auto_punctuate=True,
        )
        self._emit(
            Result(
                cleaned.text,
                raw,
                job,
                elapsed,
                changed_by_cleanup=cleaned.changed,
            )
        )

    @classmethod
    def _is_junk(cls, raw: str, seconds: float) -> bool:
        text = (raw or "").strip()
        if not text or text.lower() in cls.JUNK_TOKENS:
            return True
        return seconds >= 1.0 and len(text) <= 2

    def _forced_script(self) -> str | None:
        code = str(self.settings.get("language", AUTO) or AUTO)
        return None if code == AUTO else script_for_code(code)

    def reset_language_memory(self) -> None:
        self._tracker.reset()

    @property
    def session_script(self) -> str | None:
        return self._tracker.session_script

    def _transcribe(self, audio: np.ndarray):
        import torch

        waveform = np.ascontiguousarray(audio, dtype=np.float32)
        seconds = waveform.size / float(SAMPLE_RATE)
        forced = self._forced_script()
        if self._masker is None:
            return self._plain_transcribe(waveform)

        script = forced
        used_prior = False
        if script is None:
            prior = self._tracker.prior_for(seconds)
            if prior is not None:
                script = prior
                used_prior = True

        try:
            with torch.inference_mode():
                output = decoding.transcribe(self.model, waveform, self._masker, script)
        except Exception:
            traceback.print_exc()
            return self._plain_transcribe(waveform)

        text = output["text"]
        # A hard script mask can occasionally produce an empty decode on a
        # very short clip. Preserve the utterance by retrying unconstrained.
        if script and not str(text).strip():
            with torch.inference_mode():
                output = decoding.transcribe(self.model, waveform, self._masker, None)
            text = output["text"]

        detected = decoding.dominant_script(text)
        if forced is None and not used_prior:
            chosen = self._tracker.observe(detected, seconds, len(output.get("tokens") or []))
            if chosen and chosen != detected:
                try:
                    with torch.inference_mode():
                        output = decoding.transcribe(self.model, waveform, self._masker, chosen)
                    text = output["text"]
                    detected = decoding.dominant_script(text) or chosen
                except Exception:
                    traceback.print_exc()

        hypothesis = decoding.Hypothesis(text, output.get("timestamp"))
        hypothesis.script = detected
        hypothesis.prior_applied = used_prior
        return hypothesis

    def _plain_transcribe(self, waveform: np.ndarray):
        import torch

        try:
            with torch.inference_mode():
                return self.model.transcribe(
                    [waveform],
                    return_hypotheses=True,
                    timestamps=True,
                )[0]
        except Exception:
            with torch.inference_mode():
                return self.model.transcribe([waveform], return_hypotheses=True)[0]

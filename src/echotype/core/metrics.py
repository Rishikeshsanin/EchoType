from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class TranscriptMetrics:
    transcription_seconds: float
    audio_seconds: float
    rtf: float
    words: int
    device: str
    precision: str
    snr_db: float | None
    language: str
    script: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def calculate_metrics(
    *,
    transcription_seconds: float,
    audio_seconds: float,
    words: int,
    device: str,
    precision: str,
    snr_db: float | None = None,
    language: str = "unknown",
    script: str = "unknown",
) -> TranscriptMetrics:
    """Calculate a normalized benchmark record without requiring model/audio imports."""

    transcription_seconds = float(transcription_seconds)
    audio_seconds = float(audio_seconds)
    words = int(words)
    if transcription_seconds < 0:
        raise ValueError("transcription_seconds must be non-negative")
    if audio_seconds <= 0:
        raise ValueError("audio_seconds must be greater than zero")
    if words < 0:
        raise ValueError("words must be non-negative")

    normalized_device = str(device).strip().lower()
    normalized_precision = str(precision).strip().lower()
    if normalized_device not in {"cpu", "cuda"}:
        raise ValueError("device must be cpu or cuda")
    if normalized_precision not in {"fp16", "fp32"}:
        raise ValueError("precision must be fp16 or fp32")
    if normalized_device == "cpu" and normalized_precision == "fp16":
        raise ValueError("EchoType does not support fp16 inference on CPU")

    return TranscriptMetrics(
        transcription_seconds=transcription_seconds,
        audio_seconds=audio_seconds,
        rtf=transcription_seconds / audio_seconds,
        words=words,
        device=normalized_device,
        precision=normalized_precision,
        snr_db=None if snr_db is None else float(snr_db),
        language=str(language or "unknown").strip() or "unknown",
        script=str(script or "unknown").strip() or "unknown",
    )

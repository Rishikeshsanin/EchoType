from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass

import numpy as np

SAMPLE_RATE = 16_000
BLOCK = 480
PREROLL_SECONDS = 0.4
NOISE_PROFILE_SECONDS = 1.5
DENOISE_SNR_CEILING = 22.0
DENOISE_SNR_HARSH = 6.0


class AudioError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AudioSnapshot:
    """A thread-safe, read-only view of the live capture telemetry."""

    level: float
    peak: float
    elapsed: float
    waveform: tuple[float, ...]


def _highpass(x: np.ndarray, sr: int = SAMPLE_RATE, cutoff: float = 80.0) -> np.ndarray:
    try:
        from scipy.signal import butter, sosfilt

        sos = butter(4, cutoff / (sr / 2.0), btype="highpass", output="sos")
        return np.asarray(sosfilt(sos, x), dtype=np.float32)
    except Exception:
        return (x - float(np.mean(x))).astype(np.float32) if x.size else x


def _denoise(
    x: np.ndarray,
    noise: np.ndarray | None,
    strength: float,
    sr: int = SAMPLE_RATE,
) -> np.ndarray:
    try:
        import noisereduce as nr

        kwargs = {
            "y": x,
            "sr": sr,
            "stationary": True,
            "prop_decrease": float(np.clip(strength, 0.0, 1.0)),
        }
        if noise is not None and noise.size >= sr // 4:
            kwargs["y_noise"] = noise
        out = np.asarray(nr.reduce_noise(**kwargs), dtype=np.float32)
        if out.size == x.size and np.isfinite(out).all():
            return out
    except Exception:
        pass
    return x


def denoise_strength_for(snr_db: float, configured: float) -> float:
    configured = float(np.clip(configured, 0.0, 1.0))
    if snr_db >= DENOISE_SNR_HARSH:
        return min(configured, 0.5)
    return min(max(configured, 0.8), 1.0)


def estimate_snr_db(signal: np.ndarray, noise: np.ndarray | None) -> float:
    if signal is None or signal.size == 0:
        return 0.0
    ps = float(np.mean(signal.astype(np.float64) ** 2))
    if noise is None or noise.size == 0:
        pn = float(np.percentile(signal.astype(np.float64) ** 2, 10))
    else:
        pn = float(np.mean(noise.astype(np.float64) ** 2))
    if pn <= 1e-12 or ps <= 1e-12:
        return 60.0
    return float(10.0 * np.log10(ps / pn))


def _auto_gain(x: np.ndarray, target_peak: float = 0.92, max_gain: float = 12.0) -> np.ndarray:
    if x.size == 0:
        return x
    peak = float(np.max(np.abs(x)))
    if peak < 1e-4:
        return x
    gain = min(target_peak / peak, max_gain)
    return np.clip(x * gain, -1.0, 1.0).astype(np.float32)


def vad_flags(x: np.ndarray, sr: int = SAMPLE_RATE, aggressiveness: int = 2) -> list[bool] | None:
    try:
        import webrtcvad

        vad = webrtcvad.Vad(int(np.clip(aggressiveness, 0, 3)))
        pcm = (np.clip(x, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
        frame_bytes = BLOCK * 2
        flags = [
            vad.is_speech(pcm[i : i + frame_bytes], sr)
            for i in range(0, len(pcm) - frame_bytes + 1, frame_bytes)
        ]
        return flags or None
    except Exception:
        return None


def trim_to_speech(
    x: np.ndarray,
    sr: int = SAMPLE_RATE,
    pad_ms: int = 200,
) -> tuple[np.ndarray, float]:
    if x.size == 0:
        return x, 0.0

    flags = vad_flags(x, sr)
    if not flags:
        rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
        return x, 1.0 if rms > 0.004 else 0.0

    speech_ratio = sum(flags) / float(len(flags))
    if not any(flags):
        return x, 0.0

    first = flags.index(True)
    last = len(flags) - 1 - flags[::-1].index(True)
    pad = int(sr * pad_ms / 1000.0)
    start = max(0, first * BLOCK - pad)
    end = min(int(x.size), (last + 1) * BLOCK + pad)
    return x[start:end], speech_ratio


class AudioEngine:
    """Always-open microphone capture with pre-roll and local enhancement."""

    def __init__(self, settings) -> None:
        self.settings = settings
        self._lock = threading.Lock()
        self._stream = None
        self._recording = False
        self._frames: list[np.ndarray] = []
        self._preroll = deque(maxlen=max(1, int(PREROLL_SECONDS * SAMPLE_RATE / BLOCK)))
        self._noise = deque(maxlen=max(1, int(NOISE_PROFILE_SECONDS * SAMPLE_RATE / BLOCK)))
        self._level = 0.0
        self._peak = 0.0
        self._started_at = 0.0
        self.last_begin_at = 0.0
        self.last_end_entry_at = 0.0
        self.last_buffer_closed_at = 0.0
        self.last_capture_seconds = 0.0
        self.overflow_count = 0
        self.waveform = deque([0.0] * 72, maxlen=72)
        self.last_error: str | None = None

    @staticmethod
    def list_devices() -> list[tuple[int, str]]:
        try:
            import sounddevice as sd

            return [
                (idx, str(device.get("name", f"Device {idx}")))
                for idx, device in enumerate(sd.query_devices())
                if device.get("max_input_channels", 0) > 0
            ]
        except Exception:
            return []

    def start(self) -> None:
        import sounddevice as sd

        self.stop()
        device = self.settings.get("input_device")
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=BLOCK,
                device=device,
                callback=self._callback,
                latency="low",
            )
            self._stream.start()
            self.last_error = None
        except Exception as exc:
            self._stream = None
            self.last_error = str(exc)
            raise AudioError(f"Could not open microphone: {exc}") from exc

    def stop(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

    @property
    def running(self) -> bool:
        return self._stream is not None and bool(getattr(self._stream, "active", False))

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
        del frames, time_info
        try:
            if status:
                self.overflow_count += 1
            block = np.asarray(indata[:, 0], dtype=np.float32).copy()
            rms = float(np.sqrt(np.mean(block.astype(np.float64) ** 2)) + 1e-12)
            peak = float(np.max(np.abs(block))) if block.size else 0.0

            with self._lock:
                level_alpha = 0.5 if rms > self._level else 0.15
                peak_alpha = 0.7 if peak > self._peak else 0.12
                self._level = (1 - level_alpha) * self._level + level_alpha * rms
                self._peak = (1 - peak_alpha) * self._peak + peak_alpha * peak
                self.waveform.append(min(rms * 12.0, 1.0))
                if self._recording:
                    self._frames.append(block)
                else:
                    self._preroll.append(block)
                    if rms < 0.02:
                        self._noise.append(block)
        except Exception:
            pass

    def begin(self) -> None:
        started = time.perf_counter()
        with self._lock:
            self._frames = list(self._preroll)
            self._recording = True
            self._started_at = started
            self.last_begin_at = started
            self._peak = 0.0

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._recording

    @property
    def elapsed(self) -> float:
        with self._lock:
            return time.perf_counter() - self._started_at if self._recording else 0.0

    @property
    def level(self) -> float:
        with self._lock:
            return self._level

    @property
    def peak(self) -> float:
        with self._lock:
            return self._peak

    def snapshot(self) -> AudioSnapshot:
        """Return live meter data without exposing mutable capture buffers."""
        with self._lock:
            elapsed = time.perf_counter() - self._started_at if self._recording else 0.0
            return AudioSnapshot(
                level=self._level,
                peak=self._peak,
                elapsed=elapsed,
                waveform=tuple(self.waveform),
            )

    def noise_profile(self) -> np.ndarray | None:
        with self._lock:
            if not self._noise:
                return None
            try:
                return np.concatenate(list(self._noise))
            except Exception:
                return None

    def end(self) -> np.ndarray:
        entered = time.perf_counter()
        with self._lock:
            if not self._recording:
                return np.zeros(0, dtype=np.float32)
            self.last_end_entry_at = entered
            self._recording = False
            frames, self._frames = self._frames, []
            # The callback uses this same lock. Samples arriving after this
            # timestamp can update ambient telemetry/pre-roll only; they can
            # never mutate the detached completed utterance.
            self.last_buffer_closed_at = time.perf_counter()
            self.last_capture_seconds = max(0.0, self.last_buffer_closed_at - self.last_begin_at)
        if not frames:
            return np.zeros(0, dtype=np.float32)
        try:
            return np.concatenate(frames).astype(np.float32)
        except Exception:
            return np.zeros(0, dtype=np.float32)

    def cancel(self) -> None:
        with self._lock:
            self._recording = False
            self._frames = []

    def process(self, audio: np.ndarray) -> tuple[np.ndarray, dict[str, float | bool]]:
        raw_seconds = audio.size / float(SAMPLE_RATE)
        info: dict[str, float | bool] = {
            "raw_seconds": raw_seconds,
            "speech_ratio": 1.0,
            "denoised": False,
            "trimmed": False,
            "seconds": raw_seconds,
        }
        if audio.size == 0:
            info["speech_ratio"] = 0.0
            return audio, info

        if self.settings.get("highpass", True):
            audio = _highpass(audio)

        noise_ref = self.noise_profile()
        snr_db = estimate_snr_db(audio, noise_ref)
        info["snr_db"] = snr_db
        if self.settings.get("denoise", True) and snr_db < DENOISE_SNR_CEILING:
            strength = denoise_strength_for(
                snr_db,
                self.settings.get("denoise_strength", 0.75),
            )
            before = audio
            audio = _denoise(audio, noise_ref, strength)
            info["denoise_strength"] = strength
            info["denoised"] = audio is not before

        trimmed, ratio = trim_to_speech(audio)
        info["speech_ratio"] = ratio
        if self.settings.get("vad_trim", True) and trimmed.size >= SAMPLE_RATE * 0.15:
            audio = trimmed
            info["trimmed"] = True

        if self.settings.get("auto_gain", True):
            audio = _auto_gain(audio)

        info["seconds"] = audio.size / float(SAMPLE_RATE)
        return audio, info

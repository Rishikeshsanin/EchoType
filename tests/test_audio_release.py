from __future__ import annotations

import numpy as np

from echotype.core.audio import BLOCK, AudioEngine


class FakeSettings:
    def get(self, _key: str, default: object = None) -> object:
        return default


def microphone_block(value: float) -> np.ndarray:
    return np.full((BLOCK, 1), value, dtype=np.float32)


def test_samples_after_end_cannot_append_to_completed_utterance() -> None:
    audio = AudioEngine(FakeSettings())
    audio.begin()
    audio._callback(microphone_block(0.1), BLOCK, None, None)

    completed = audio.end()
    closed_size = completed.size
    closed_copy = completed.copy()
    audio._callback(microphone_block(0.9), BLOCK, None, None)

    assert audio.is_recording is False
    assert completed.size == closed_size == BLOCK
    np.testing.assert_array_equal(completed, closed_copy)
    closed_at = audio.last_buffer_closed_at
    capture_seconds = audio.last_capture_seconds
    assert audio.end().size == 0
    assert audio.last_buffer_closed_at == closed_at
    assert audio.last_capture_seconds == capture_seconds
    assert audio.last_end_entry_at <= audio.last_buffer_closed_at


def test_cancel_discards_current_frames_but_keeps_stream_telemetry_safe() -> None:
    audio = AudioEngine(FakeSettings())
    audio.begin()
    audio._callback(microphone_block(0.2), BLOCK, None, None)
    audio.cancel()
    audio._callback(microphone_block(0.3), BLOCK, None, None)

    assert audio.is_recording is False
    assert audio.end().size == 0
    assert audio.snapshot().level > 0.0

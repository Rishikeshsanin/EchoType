# Recording overlay

EchoType's system-wide recording overlay is implemented in `echotype.ui.overlay` and is
fed exclusively by the existing `AudioEngine`. It does not open a microphone stream or
record audio itself.

## Runtime integration

`DictationRuntime.overlay_state` emits `(state, payload)` and `app.main` connects that
signal to `RecordingOverlay.set_state`. Supported states are `hidden`, `listening`,
`processing` (or the alias `transcribing`), `success`, `cancelled`, and `error`.

Payloads may contain:

- `target_hwnd`, `target_title`, and `target_process` for app naming and monitor placement
- `detail` for the secondary status line
- `dismiss_ms` to override terminal-state display time

The overlay polls `AudioEngine.snapshot()` on a 33 ms Qt timer. The snapshot is a
thread-safe read of level, peak, elapsed time, and the existing waveform history.

The widget is frameless, topmost, transparent to pointer input, and configured not to
accept or activate focus. On Windows it also applies `WS_EX_NOACTIVATE`,
`WS_EX_TOOLWINDOW`, and `WS_EX_TRANSPARENT`. It is positioned above the available-area
bottom edge of the target application's monitor (or the cursor/primary monitor fallback).

## Manual validation

1. Start EchoType and wait for the speech model to become ready.
2. Focus Notepad, Chrome, or VS Code on each monitor in turn.
3. Hold Right Shift and verify the overlay appears without moving keyboard focus.
4. Speak and confirm the timer and bars respond without interrupting capture.
5. Release Right Shift and confirm `TRANSCRIBING` remains visible until delivery finishes.
6. Verify a brief `DONE` state appears after paste, then the overlay disappears.
7. Hold Right Shift and press Escape; confirm the cancelled state dismisses cleanly.
8. At 125%, 150%, and 200% Windows scaling, confirm the card remains compact and inside
   the monitor's available work area.

Automated tests cover state transitions, timer formatting, and target application naming;
microphone response, Windows focus behavior, and paste delivery require this live test.

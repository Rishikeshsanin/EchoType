# Architecture and QA boundaries

EchoType keeps UI concerns separate from capture, inference, and persistence. This document describes
the audited `develop` baseline and the boundaries tests rely on.

```text
Qt UI / feature pages
        |
        v  signals/slots
DictationRuntime
  |       |        |          |
  v       v        v          v
Audio   ASR     Hotkeys   Windows Injector
  |       |                   |
  |       v                   v
  |   cleanup/script       clipboard + captured HWND
  |   tracking
  v
temporary in-memory waveform

Successful result --> privacy gate --> local HistoryStore
Settings ----------> per-user atomic JSON
```

## Trust and storage boundaries

- Audio blocks and ambient-noise samples are held in memory. The normal pipeline does not write raw
  microphone audio to the repository or application-data directory.
- On Windows, settings are stored at `%LOCALAPPDATA%\EchoType\settings.json`; history is plaintext
  JSONL at `%LOCALAPPDATA%\EchoType\history.jsonl`. Current entries include both cleaned transcript and
  raw decoder text, which should be treated as equally sensitive.
- On non-Windows developer/CI hosts, the XDG data directory is used. Production paste-back remains
  Windows-first.
- Speech model artifacts and model-provided Python code are managed by the Hugging Face cache.
- Hugging Face tokens are read from `HF_TOKEN` or `HUGGING_FACE_HUB_TOKEN`; EchoType does not load a
  repository `.env` file. Diagnostic output redacts common token shapes and the user-home path.
- Settings are written through a temporary sibling file and `os.replace`. History is append-only until
  explicit clear/delete operations.
- Windows target capture currently identifies only the top-level HWND/title/PID. It does not identify
  whether the caret is inside a password or secret input control, so sensitive-target handling remains
  an explicit release security gap.

## Model loading boundary

`TranscriptionEngine` imports Torch and Transformers only when the background load begins. The model
uses `trust_remote_code=True`, making immutable revision handling a security boundary, not merely a
reproducibility preference.

The audited baseline resolves and persists an immutable revision for
`SharadhNaiduTrains/sravaani-flow-model`. The helper accepts only 40–64 character hexadecimal commit
SHAs. The fallback `ARTPARK-IISc/SraVaani-1.0` still lacks a separate persisted/pinned revision and is a
release blocker.

## Hardware-independent test seams

- Cleanup, language/script descriptions, session tracking, settings, history, diagnostics, model
  revision validation, and benchmark metrics are pure or file-local tests.
- Runtime privacy/metadata tests load the real runtime module with fake Qt, audio, transcription,
  hotkey, and injection boundaries.
- Injection tests replace clipboard, focus, paste, type, and sleep helpers before calling `deliver`.
- Hotkey tests call key-resolution and press/release handlers directly; they never start a listener.
- CI sets Hugging Face and Transformers offline flags and installs no Torch, model, CUDA, microphone,
  or PySide runtime.

This design lets CI detect policy regressions without claiming that global hooks, device drivers,
real focus restoration, Unicode paste behavior, or model quality have been validated.

## Transcript and benchmark metadata

Runtime results currently calculate mode, raw text, processing duration, RTF, processed audio
duration, SNR, denoise flag, cleanup-changed flag, target title, device, and precision. The release UI
must also expose word count, selected language, and detected script. `core.metrics.calculate_metrics`
provides a hardware-independent validated record for benchmark capture; it rejects impossible
CPU/FP16 combinations and non-positive audio duration.

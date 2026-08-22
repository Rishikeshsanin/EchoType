# EchoType

**Privacy-first offline AI voice typing for desktop applications.**

EchoType is a modern Windows dictation application that captures speech locally, converts it into text, improves the transcript when requested, and delivers it directly to the application you were using — without requiring a cloud speech API for normal dictation.

> **Speak naturally. Type anywhere.**

## Project status

🚧 **EchoType V2 is in active development.**

The first live-engine checkpoint is implemented on the `develop` branch and reviewed through draft PR #1. The new PySide6 interface is connected to the migrated microphone, speech-recognition, cleanup, hotkey, history, and Windows paste-back services.

**Not release-ready yet:** the full microphone → SraVaani → paste loop still needs hardware validation on fresh Windows CPU/CUDA environments before this work can merge to `main`.

## Current V2 Dictate pipeline

```text
Global hotkey / hold-to-record
        ↓
Microphone capture + 400 ms pre-roll
        ↓
80 Hz high-pass + SNR-aware denoise + VAD + auto gain
        ↓
SraVaani local inference (CPU or NVIDIA CUDA)
        ↓
Script-aware decoding + short-utterance session memory
        ↓
Verbatim or Smart text processing
        ↓
Local transcript/history
        ↓
Restore original Windows app → paste at caret
```

## What is implemented on `develop`

- Modern native PySide6/Qt application shell
- System-wide push-to-talk with **Right Shift** by default
- F9 toggle dictation, F11 repaste, Esc cancel service support
- Local microphone capture with pre-roll
- SNR-aware adaptive denoising
- WebRTC VAD trimming and automatic gain
- SraVaani inference worker with CPU/CUDA selection
- Script-constrained decoding for selected languages
- Sticky session-script prior for ambiguous short utterances
- **Verbatim** mode that avoids semantic cleanup
- **Smart** mode with punctuation, safe filler handling, compound fixes, and vocabulary corrections
- Raw transcript preserved separately from transformed text
- Focus-aware Windows paste-back
- Local transcript history outside the repository
- Private-session and history-disable runtime controls
- Model mirror SHA resolved and persisted per installation during development
- Python 3.11/3.12 Windows CI and behavioral tests

## Development quick start

EchoType V2 currently targets **Windows 10/11 with Python 3.11 or 3.12**.

```bat
git clone https://github.com/Rishikeshsanin/EchoType.git
cd EchoType
git checkout develop
setup.bat
run.bat
```

`setup.bat` creates `.venv`, installs the tested PyTorch 2.6.0 CPU build or CUDA 12.4 build when an NVIDIA GPU is detected, installs EchoType, and verifies core imports.

On the first launch, the speech model may need to be downloaded and cached. Keep an internet connection available for that first model fetch. Normal inference is intended to run locally after the model is cached.

### Try the Dictate loop

1. Start EchoType with `run.bat`.
2. Wait for the model chip to show a ready compute state such as `CPU / FP32` or `CUDA / FP16`.
3. Focus Notepad or another normal desktop text field.
4. Hold **Right Shift**, speak, then release it.
5. The transcript should appear in EchoType and be pasted back into the application that had focus when recording started.

Because this branch is still a development checkpoint, report any microphone, model-load, CUDA, focus, or paste failure before treating the loop as stable.

## Text modes

### Verbatim

Preserves the speaker's wording. EchoType only normalizes decoder whitespace and avoids filler removal, grammar-style rewrites, and automatic semantic cleanup.

### Smart

Uses local deterministic cleanup for punctuation, repeated speech, selected filler handling, casing, compounds, contractions, and custom vocabulary.

### Notes

A Notes mode entry point exists in the V2 architecture, but Notes-specific structural formatting is still on the roadmap. It currently must not be treated as finished smart summarization.

## Language handling

EchoType preserves the reference implementation's useful script-constrained decoder, but V2 deliberately distinguishes **script detection** from **true language identification**.

For example, Devanagari output is evidence of a writing script, not proof that the speaker used Hindi; Marathi, Nepali, Sanskrit, and other languages can use the same script. True language identification and code-switched dictation are separate V2 roadmap items.

## Privacy

EchoType is designed around local inference and local application data.

- Microphone audio is processed locally during normal dictation.
- Settings and transcript history are stored in the user's application-data directory, not inside the Git repository.
- `.env`, environments, runtime history, settings, caches, and build output are ignored by Git.
- Private-session and history-disable controls already exist at the runtime layer; their full UI is still being built.

## V2 architecture

```text
src/echotype/
├── app/
│   ├── main.py          # Qt bootstrap
│   └── runtime.py       # service orchestration / UI boundary
├── ui/
│   ├── main_window.py   # native product shell
│   └── theme.py         # centralized visual system
├── core/
│   ├── audio.py         # capture and local enhancement
│   ├── transcription.py # asynchronous SraVaani worker
│   ├── decoding.py      # script-constrained TDT decoding
│   ├── cleanup.py       # mode-aware deterministic text processing
│   └── languages.py     # language/script metadata
└── services/
    ├── hotkeys.py       # global shortcuts
    ├── injection.py     # Windows focus + paste-back
    ├── settings.py      # atomic per-user settings
    └── history.py       # local transcript persistence
```

The key design rule is that Qt widgets do not own the speech engine. UI changes communicate with the runtime through signals, while audio, ASR, persistence, keyboard hooks, and Windows integration remain separate services.

## V2 direction

EchoType is being redesigned around six goals:

1. **Modern native desktop experience** — polished PySide6/Qt UI, clear recording states, onboarding, tray integration, and responsive layouts.
2. **Reliable dictation engine** — preserve and improve the proven local speech, audio-processing, hotkey, and cursor-injection pipeline.
3. **Better language intelligence** — distinguish script detection from actual language identification and improve multilingual/code-switched dictation.
4. **Flexible text modes** — Verbatim, Smart Dictation, and Notes-oriented processing instead of forcing one cleanup policy on every transcript.
5. **Privacy and safety** — local-first history controls, safer model loading, diagnostics, and explicit data-retention options.
6. **Real product distribution** — automated tests, CI, benchmarks, packaged Windows builds, releases, and a simple installer experience.

## Acknowledgements

EchoType is being developed with permission from **Sharadh Naidu** as a substantially redesigned and extended application based on the ideas and working implementation in [`SharadhNaidu/srivaani-demo`](https://github.com/SharadhNaidu/srivaani-demo).

The reference implementation remains credited for its original work, including its offline dictation workflow and several engineering ideas that EchoType preserves or reworks.

Speech recognition is powered by **ARTPARK-IISc SraVaani-1.0**. All model credit belongs to its original authors and maintainers.

This repository is intentionally separate from the original project so EchoType's new architecture, interface, features, fixes, experiments, and release history can be developed independently while keeping attribution explicit.

## Roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the staged V2 plan.

---

**EchoType** — Speak naturally. Type anywhere.

# EchoType

**Privacy-first offline AI voice typing for desktop applications.**

EchoType is being built as a modern desktop dictation application that captures speech locally, converts it into text, improves the transcript, and delivers it directly to the active application without requiring a cloud speech API.

> **Speak naturally. Type anywhere.**

## Project status

🚧 **Active V2 development** — the new EchoType application is currently being designed and built.

The first milestone focuses on preserving the strongest parts of the working reference implementation while replacing its weaker product, architecture, security, and user-experience layers.

## What EchoType is designed to do

- Offline speech-to-text after the model has been downloaded
- System-wide push-to-talk dictation
- Multilingual Indian-language speech recognition
- CPU and NVIDIA CUDA inference paths
- Local audio enhancement, voice activity detection, and gain normalization
- Language/script-aware decoding
- Smart transcript cleanup and custom vocabulary
- Paste dictated text into the application that was active when recording began
- Local notes and transcription history
- Privacy-focused operation with no cloud speech API required

## V2 direction

EchoType is being redesigned around six goals:

1. **Modern native desktop experience** — a polished PySide6/Qt interface, clear recording states, onboarding, tray integration, and responsive layouts.
2. **Reliable dictation engine** — preserve and improve the proven local speech, audio-processing, hotkey, and cursor-injection pipeline.
3. **Better language intelligence** — distinguish script detection from actual language identification and improve multilingual/code-switched dictation.
4. **Flexible text modes** — Verbatim, Smart Dictation, and Notes-oriented processing instead of forcing one cleanup policy on every transcript.
5. **Privacy and safety** — local-first history controls, safer model loading, version pinning, diagnostics, and explicit data-retention options.
6. **Real product distribution** — automated tests, CI, benchmarks, packaged Windows builds, releases, and a simple installer experience.

## Planned application areas

- **Dictate** — push-to-talk voice typing with waveform and transcription status
- **Notes** — local voice-assisted note taking
- **History** — searchable transcript history with copy, repaste, filter, export, and delete controls
- **Vocabulary** — reusable terminology profiles for domains such as software development, academics, and custom names
- **Analytics** — local statistics such as words dictated, latency, real-time factor, and estimated typing time saved
- **Settings** — audio, languages, text processing, shortcuts, privacy, compute, model, and diagnostics controls

## Technical direction

The V2 architecture will separate UI, core speech processing, and desktop services so the interface can evolve without destabilizing transcription.

```text
src/echotype/
├── app/          # bootstrap, lifecycle, application state
├── ui/           # windows, pages, widgets, themes
├── core/         # ASR, audio, decoding, cleanup, languages
├── services/     # hotkeys, injection, history, settings, diagnostics
└── storage/      # local application data and migrations
```

## Privacy

EchoType is intended to run speech recognition locally. After the speech model is available on the machine, normal dictation should not require sending microphone audio to a remote speech service.

V2 will also add explicit controls for local transcript history, private sessions, retention, and deletion.

## Acknowledgements

EchoType is being developed with permission from **Sharadh Naidu** as a substantially redesigned and extended application based on the ideas and working implementation in [`SharadhNaidu/srivaani-demo`](https://github.com/SharadhNaidu/srivaani-demo).

The reference implementation remains credited for its original work, including its offline dictation workflow and several engineering ideas that EchoType will preserve or rework.

Speech recognition is powered by **ARTPARK-IISc SraVaani-1.0**. All model credit belongs to its original authors and maintainers.

This repository is intentionally separate from the original project so EchoType's new architecture, interface, features, fixes, experiments, and release history can be developed independently while keeping attribution explicit.

## Development roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the staged V2 plan.

---

**EchoType** — Speak naturally. Type anywhere.

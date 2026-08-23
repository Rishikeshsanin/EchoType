# EchoType

**Offline multilingual AI voice typing for Windows.**

> Speak naturally. Type anywhere.

EchoType is a privacy-first desktop dictation application. Hold a global shortcut, speak, release,
and EchoType transcribes locally with SraVaani, applies the selected text mode, then returns the text
to the Windows application that had focus when recording began.

## Release status

**EchoType v0.9.0 Beta** is a release candidate awaiting the final manual Windows validation listed
in [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md). It is beta software: do not use it as the
only copy of important text, and review a transcript before relying on it.

No final tag or GitHub Release has been published from this branch yet.

## Screenshots

The release screenshot set is structured around these states:

1. **Dictate / Ready** — language dropdown, modes, transcript workspace, input and shortcuts
2. **Listening** — responsive voice spikes, timer, and target-application overlay
3. **Transcribing** — previous transcript clearly separated from the in-progress utterance
4. **History and Notes** — local transcript review, repaste, and note capture
5. **Vocabulary and Settings** — terminology profiles, privacy, audio, compute, and appearance

Final screenshots will be captured after the manual release gate so they represent the shipped build.

## Highlights

- Native PySide6 interface with dark, light, and system themes
- System-wide push-to-talk and toggle dictation
- Offline/local SraVaani inference after the model is cached
- CPU execution and NVIDIA CUDA/FP16 support where available
- Searchable, keyboard-accessible language dropdown with the complete backend catalog
- Verbatim, Smart, and Notes output modes
- No-focus recording/transcription overlay with recognizable target application names
- Local History, persistent Notes, vocabulary profiles, diagnostics, and session metrics
- Captured-window paste-back, F11 repaste, copy, and Send to Notes actions
- Private session, history disable/retention, and conservative sensitive-target blocking
- Immutable model revision resolution before any model-provided remote code is executed

## How dictation works

```text
Hold Right Shift (default)
        ↓
In-memory microphone capture + 400 ms pre-roll
        ↓
High-pass filter + SNR-aware denoise + VAD trim + auto gain
        ↓
Local SraVaani inference on CPU or NVIDIA CUDA
        ↓
Selected script constraint / truthful script presentation
        ↓
Verbatim, Smart, or Notes cleanup
        ↓
Local transcript → restore captured app → paste at caret
```

The microphone stream may stay open for pre-roll, ambient level telemetry, and a noise profile.
That is distinct from recording: releasing push-to-talk closes the current utterance buffer
immediately, stops the listening meter/timer, and changes the UI to Transcribing.

## Languages

Auto-detect is the first option. Popular languages are pinned near the top, and every backend
language remains searchable and scrollable.

**Popular:** English, Hindi, Telugu, Kannada, Tamil, Malayalam, Bengali, Marathi, Gujarati, Punjabi,
Odia, and Assamese.

**Complete catalog:** Angami, Ao, Assamese, Auto-detect, Awadhi, Bajjika, Bearybashe, Bengali,
Bhili, Bhojpuri, Bodo, Bundeli, Chakhesang, Chakma, Chhattisgarhi, Dogri, English, Garo, Garhwali,
Gondi, Gujarati, Halbi, Haryanvi, Hindi, Idu Mishmi, Kannada, Karbi, Khariboli, Khortha, Kokborok,
Konkani, Kurukh, Magadhi, Maithili, Malayalam, Malvani, Manipuri, Marathi, Marwari, Mizo, Nagamese,
Nepali, Nyishi, Odia, Punjabi, Rajasthani, Rengma, Rongmei, Sadri, Sambalpuri, Sanskrit, Santali,
Sindhi, Sumi, Surgujia, Surjapuri, Tagin, Tamil, Telugu, Tulu, and Wancho.

Manual selection constrains the decoder to the associated writing script. Auto-detect uses script
evidence and short-utterance session context; EchoType does **not** claim that script detection is
true language identification. Devanagari, Bengali, Kannada, and Latin scripts can each represent
multiple languages.

## Output modes

### Verbatim

Keeps the speaker's wording and performs only minimal decoder/whitespace normalization. It avoids
filler removal and semantic rewriting.

### Smart

Uses deterministic local cleanup for spoken punctuation, safe filler handling, repeated speech,
casing, compounds, contractions, and active vocabulary terms.

### Notes

Uses the local cleanup foundation and routes dictated material into the Notes workflow. Notes CRUD,
autosave, search, export, and Dictate-to-Notes hand-off are implemented. AI summarization and advanced
automatic note structuring are not implemented or advertised in this beta.

## Default global shortcuts

| Shortcut | Action |
|---|---|
| **Right Shift** | Hold to talk; release to transcribe |
| **F9** | Start or stop toggle dictation |
| **F11** | Paste the last successful transcript again |
| **Esc** | Cancel the current recording |

Shortcut assignments are configurable in Settings. EchoType rejects duplicate assignments before
saving them.

## History, Notes, Vocabulary, and Settings

- **History** stores successful transcripts locally, newest first, with search, filters, edit,
  export, delete, and repaste actions.
- **Notes** provides persistent local notes with autosave, search, export, copy, and transcript intake.
- **Vocabulary** manages built-in and custom terminology profiles with preferred spellings and aliases.
- **Settings** covers microphones, language, cleanup, shortcuts, CPU/CUDA, precision, history/privacy,
  themes, diagnostics, and model revision information.
- **Session statistics** show local utterance, word, audio, and estimated typing-time metrics.

## Installation

### Requirements

- Windows 10 or Windows 11
- 64-bit Python 3.11 or 3.12
- A working microphone
- Enough disk space for PyTorch, dependencies, and the SraVaani model cache
- Internet access for setup and the first model/revision fetch; later cached inference is local
- Optional: a compatible NVIDIA GPU and driver for the tested PyTorch CUDA 12.4 path

### Setup

```bat
git clone https://github.com/Rishikeshsanin/EchoType.git
cd EchoType
setup.bat
run.bat
```

`setup.bat` creates `.venv`, selects the tested PyTorch 2.6.0 CPU build or attempts the CUDA 12.4
build when an NVIDIA GPU is detected, installs EchoType and its declared dependencies, then runs
`verify.py`. `run.bat` starts the installed package from that environment.

On first launch, EchoType resolves immutable model commit revisions and downloads uncached model
artifacts. A cached/offline launch refuses unpinned model-provided code instead of silently executing
a mutable remote revision.

### First dictation

1. Run `run.bat` and wait for `CPU / FP32` or `CUDA / FP16` in the model status chip.
2. Focus a normal text field in Notepad or another Windows application.
3. Hold Right Shift, speak, then release it.
4. Confirm the overlay changes immediately from Listening to Transcribing.
5. Review the transcript in EchoType and at the captured caret.

## Troubleshooting

- **Model will not load:** connect once so the model and immutable revision can be resolved; check
  model access, disk space, and the Diagnostics section.
- **CUDA requested but CPU appears:** confirm the NVIDIA driver and PyTorch CUDA build. EchoType falls
  back to CPU/FP32 when CUDA warm-up fails and reports the actual device.
- **No microphone:** select an input in Settings, close other apps using exclusive microphone access,
  and check Windows microphone privacy permissions.
- **Global shortcuts unavailable:** another app may own the key or the keyboard hook may have failed;
  select different distinct shortcuts in Settings and restart if needed.
- **Text was copied but not pasted:** the original window may have closed, Windows may have refused
  focus restoration, or the field may be sensitive. The transcript remains available in EchoType.
- **Wrong script with Auto-detect:** choose a manual language constraint. Script/language accuracy is
  still being improved and no measured accuracy claim is made for this beta.
- **First launch is slow:** model download and CPU model loading can take time. Later cached launches
  avoid the model download but still need to load the model into memory.

Run `.venv\Scripts\python.exe verify.py` for a sanitized environment check.

## Privacy and security

- Normal microphone audio is processed in memory and is not saved by EchoType.
- Inference and deterministic text cleanup run locally after model artifacts are cached.
- Settings, history, notes, and vocabulary are stored under `%LOCALAPPDATA%\EchoType`, outside the
  repository.
- Private session prevents successful transcripts from being written to History.
- History can be disabled, retained indefinitely, or pruned by configured retention.
- Diagnostics redact common token shapes and the user-home path.
- Detectable standard Windows password controls are blocked. Custom-rendered browser password fields
  do not always expose their sensitive state to Win32, so blocking is conservative, not a guarantee.
- Model repositories that provide executable code must resolve to immutable commit SHAs.

## Technology and architecture

- Python 3.11/3.12
- PySide6 / Qt 6 native desktop UI
- PyTorch and Transformers
- ARTPARK-IISc SraVaani-1.0 speech recognition
- NumPy, SciPy, sounddevice, noisereduce, and WebRTC VAD
- pynput and pywin32 for global shortcuts, focus capture, and paste-back
- Validated atomic JSON/JSONL storage in the per-user application-data directory

The Qt UI communicates through signals with `DictationRuntime`. Audio capture, transcription,
cleanup, hotkeys, persistence, and Windows delivery remain separate services. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for trust, storage, and test boundaries.

## Current limitations

- Recognition accuracy varies by microphone, speaker, noise, language, and clip length; no accuracy
  benchmark is claimed for v0.9.0 Beta.
- True spoken-language identification and robust code-switched dictation are not yet implemented.
- Advanced Notes intelligence/summarization is not implemented.
- Custom-rendered password fields cannot always be identified reliably.
- Windows is the supported production platform; packaging and a signed installer are future work.
- Final Windows app/language/theme validation remains required before publishing this release.

## Roadmap and release references

- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md)
- [`docs/QA_CHECKLIST.md`](docs/QA_CHECKLIST.md)
- [`docs/RELEASE_NOTES_0.9.0.md`](docs/RELEASE_NOTES_0.9.0.md)
- [`CHANGELOG.md`](CHANGELOG.md)
- [`benchmarks/README.md`](benchmarks/README.md)

Planned work includes accuracy measurement/improvement, language identification, code-switching,
advanced Notes workflows, tray/onboarding improvements, Windows packaging, signing, and installers.

## Acknowledgements

EchoType was developed from ideas and code derived from
[`SharadhNaidu/srivaani-demo`](https://github.com/SharadhNaidu/srivaani-demo) with permission and has
since been substantially redesigned and extended.

- **EchoType developer:** Rishikesh
- **Original/reference application:** Sharadh Naidu
- **Speech recognition:** [ARTPARK-IISc SraVaani-1.0](https://huggingface.co/ARTPARK-IISc/SraVaani-1.0)

Repository provenance and the distinction between application authorship and model attribution are
also preserved in [`NOTICE.md`](NOTICE.md).

## License and distribution status

No standalone software license has been selected for EchoType yet. See [`NOTICE.md`](NOTICE.md) for
the current repository licensing and attribution status. The absence of a license means reuse and
redistribution rights should not be assumed.

---

**EchoType v0.9.0 Beta** — Speak naturally. Type anywhere.

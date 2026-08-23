# EchoType v0.9.0 Beta

Speak naturally. Type anywhere.

EchoType v0.9.0 Beta is the first public-release candidate for the redesigned privacy-first Windows
voice-typing application. It combines a native desktop interface with local SraVaani speech
recognition, global shortcuts, captured-window paste-back, and local productivity tools.

## Highlights

- Hold Right Shift, speak, and release to transcribe and paste into the app where dictation began.
- Run speech recognition locally on CPU or supported NVIDIA CUDA hardware after model setup.
- Choose Auto-detect or search the complete supported language catalog.
- See clear Listening, Transcribing, Done, Cancelled, and Error states without the overlay taking focus.
- Keep successful transcripts in local History, send them to Notes, and correct terminology with
  reusable Vocabulary profiles.
- Control local persistence with private session, history disable, retention, and deletion settings.

## What's new

### Native desktop experience

EchoType now uses PySide6/Qt with a compact Windows utility layout, multilingual typography, a
recognizable language dropdown, dark/light/system themes, a transcript workspace, session statistics,
recent History, local Notes, Vocabulary, Settings, and Diagnostics.

The input visualization uses the existing microphone telemetry to show responsive voice spikes,
quiet input, and clipping. Releasing push-to-talk immediately ends the Listening meter/timer and
switches to Transcribing, even though the microphone stream can remain available for pre-roll and
ambient noise measurement.

### Dictation workflows

- **Verbatim:** preserves wording with minimal normalization.
- **Smart:** applies deterministic local punctuation and safe cleanup.
- **Notes:** supports the Notes capture path using deterministic cleanup; advanced AI structuring is
  not included.
- **Right Shift:** hold to talk.
- **F9:** toggle dictation.
- **F11:** paste the last successful transcript again.
- **Esc:** cancel recording without submitting, copying, pasting, or persisting the clip.

Shortcuts are configurable and rendered from the saved settings.

### Language and script handling

Auto-detect remains first, popular languages are easy to reach, and all backend regional languages
remain searchable. Manual language selection constrains the decoder's writing script. Script evidence
is presented truthfully and is not described as independent spoken-language identification.

### Target-window delivery

EchoType retains the Windows target captured at recording start and restores that window before
paste-back. The overlay now prefers recognizable window/product titles such as Notepad and Visual
Studio Code over generic host processes such as Python, pythonw, or ApplicationFrameHost. EchoType's
own window and overlay are excluded from external paste targets.

## Supported workflows

- Global dictation into normal Windows text fields
- Copy-only use with automatic paste disabled
- Repaste of the last successful transcript
- Search, filter, edit, export, delete, and repaste from local History
- Persistent note creation, autosave, search, copy, export, and Dictate-to-Notes hand-off
- Built-in and custom vocabulary profiles
- CPU, automatic device choice, and explicit CUDA settings
- Private session and history-disabled dictation

## Privacy and local AI

Normal audio capture and inference run locally. EchoType holds microphone samples in memory and does
not save raw recordings. Settings, History, Notes, and Vocabulary are stored under the user's local
application-data directory, not in the repository.

Model artifacts may require a network connection on first setup. Because the speech model uses
model-provided code, EchoType resolves and persists immutable commit revisions and refuses to execute
an unpinned mutable revision. Diagnostics redact common token patterns and user-home paths.

Detectable standard Windows password fields are blocked conservatively. Custom-rendered password
fields in browsers and other applications cannot always be identified.

## Testing status

The release-preparation branch passes 142 hardware-independent Python, Qt offscreen, privacy,
storage, hotkey, audio-boundary, overlay, UI integration, and syntax tests. Offscreen construction was
checked at 940×640, 1280×800, 1366×768, and 1600×900 in dark, light, and system themes. Tests do not
claim microphone, global-hook, model-quality, or real focus-restoration coverage.

Previous user testing on Windows confirmed application launch, PySide6 rendering, CUDA/FP16 on an
NVIDIA GeForce MX330, Right Shift push-to-talk, transcription, global paste-back, and readable Telugu,
Kannada, and Devanagari output. The broader final manual language/app/shortcut/theme matrix remains
explicitly unchecked in [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md); this release must not be tagged
or published until that validation is completed.

## Known limitations

- Recognition accuracy varies and has not been benchmarked for a public accuracy claim.
- Accuracy tuning, true language identification, and code-switching are future work.
- Advanced Notes intelligence and automatic structuring are not implemented.
- Custom password fields cannot always expose their sensitive state to EchoType.
- Windows packaging, code signing, automatic updates, and an installer are future work.
- The beta is distributed from source and requires Python 3.11 or 3.12.

## Credits

EchoType was developed by **Rishikesh** from ideas and code derived from
[`SharadhNaidu/srivaani-demo`](https://github.com/SharadhNaidu/srivaani-demo) with permission and has
since been substantially redesigned and extended.

- Original/reference application: **Sharadh Naidu**
- Speech recognition: **ARTPARK-IISc SraVaani-1.0**

See `NOTICE.md` in the repository for complete attribution and current licensing status.

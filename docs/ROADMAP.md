# EchoType V2 Roadmap

EchoType will be upgraded in stages so the working offline dictation pipeline remains recoverable while the application is redesigned.

## Phase 0 — Provenance and baseline

- [x] Create standalone EchoType repository
- [x] Add explicit attribution to Sharadh Naidu and the original `srivaani-demo` project
- [x] Add ARTPARK-IISc / SraVaani-1.0 acknowledgement
- [x] Keep licensing status explicit rather than assuming the model license applies to application code
- [ ] Import/adapt the working reference implementation into a protected baseline
- [ ] Verify microphone → transcription → cleanup → cursor injection end-to-end
- [ ] Record baseline CPU/GPU load, latency, RTF, and test results

## Phase 1 — Foundation and security

- [ ] Create `develop` branch and keep `main` release-oriented
- [ ] Introduce `src/echotype` package layout
- [ ] Separate application/UI state from speech engine and Windows services
- [ ] Pin the SraVaani model revision used by EchoType
- [ ] Remove unpinned remote-code execution from the normal model-loading path where practical
- [ ] Move settings/history/cache to proper per-user application-data locations
- [ ] Add structured logging and a diagnostics report
- [ ] Define configuration schema and safe migrations
- [ ] Add pytest unit/integration test structure
- [ ] Add GitHub Actions for hardware-independent checks

## Phase 2 — Native UI redesign

- [ ] Replace the Tkinter product UI with PySide6/Qt
- [ ] Add modern application shell and sidebar navigation
- [ ] Add Dictate page with waveform, microphone state, selected language, active text mode, device and model status
- [ ] Add Notes page
- [ ] Add History page
- [ ] Add Vocabulary page
- [ ] Add Analytics page
- [ ] Redesign Settings into focused categories
- [ ] Add first-run onboarding
- [ ] Add modern recording/transcribing overlay
- [ ] Add tray integration and minimize-to-tray behavior
- [ ] Add scalable light/dark theme foundation
- [ ] Preserve global hotkeys and paste-to-cursor behavior

## Phase 3 — Dictation intelligence

- [ ] Add Verbatim mode
- [ ] Add Smart Dictation mode
- [ ] Add Notes mode
- [ ] Separate literal transcript from transformed transcript
- [ ] Improve punctuation and sentence segmentation
- [ ] Make cleanup transformations explainable/reversible where possible
- [ ] Add vocabulary profiles
- [ ] Add application-aware vocabulary selection
- [ ] Improve true language identification beyond script-only detection
- [ ] Experiment with code-switched English + Indian-language speech
- [ ] Measure every AI/NLP change against reproducible test audio

## Phase 4 — History, privacy, and productivity

- [ ] Searchable local transcript database
- [ ] Copy / repaste / edit / favorite / delete actions
- [ ] Language, application, and date filters
- [ ] Export TXT/Markdown
- [ ] Private session mode
- [ ] Disable-history option
- [ ] Configurable retention period
- [ ] One-click clear history
- [ ] Local usage analytics (words, utterances, latency, RTF, estimated typing time saved)

## Phase 5 — Reliability and diagnostics

- [ ] Microphone test and input-level diagnostics
- [ ] Model/GPU/driver diagnostics
- [ ] CPU/CUDA fallback validation
- [ ] Failure-safe clipboard and focus handling
- [ ] Crash-safe settings/history writes
- [ ] Performance benchmark command
- [ ] Expanded multilingual test corpus
- [ ] Regression tests for cleanup and language selection
- [ ] Windows 10/11 compatibility checks

## Phase 6 — Distribution

- [ ] Package EchoType as a Windows executable
- [ ] Build installer
- [ ] First-run model download with progress/retry/resume
- [ ] GitHub Releases
- [ ] Versioned changelog
- [ ] Release notes
- [ ] Screenshots and demo video/GIF
- [ ] Architecture diagram
- [ ] Benchmark documentation
- [ ] Final portfolio-ready README

## Release principle

**Quality > quantity.**

A feature is not considered complete until it works end-to-end, has a clear failure mode, preserves user privacy expectations, and does not regress the core dictation workflow.

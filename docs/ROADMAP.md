# EchoType V2 Roadmap

EchoType will be upgraded in stages so the working offline dictation pipeline remains recoverable while the application is redesigned.

> **Current checkpoint:** EchoType v0.9.0 Beta is prepared on `codex/v0.9-release` and awaits the
> final manual Windows release matrix before merge, tag, or publication.

## Phase 0 — Provenance and baseline

- [x] Create standalone EchoType repository
- [x] Add explicit attribution to Sharadh Naidu and the original `srivaani-demo` project
- [x] Add ARTPARK-IISc / SraVaani-1.0 acknowledgement
- [x] Keep licensing status explicit rather than assuming the model license applies to application code
- [x] Adapt the working reference engine into EchoType's separated V2 architecture
- [ ] Verify microphone → transcription → cleanup → cursor injection end-to-end on Windows hardware
- [ ] Record baseline CPU/GPU load, latency, RTF, and test results

## Phase 1 — Foundation and security

- [x] Create `develop` branch and keep `main` release-oriented
- [x] Introduce `src/echotype` package layout
- [x] Separate application/UI state from speech engine and Windows services
- [ ] Hard-pin the SraVaani model revision in release source *(development builds now resolve and persist an immutable mirror SHA per installation)*
- [ ] Remove unpinned remote-code execution from the normal model-loading path where practical
- [x] Move settings/history/cache to proper per-user application-data locations
- [x] Add a sanitized diagnostics report
- [x] Define a validated settings schema with atomic persistence
- [x] Add pytest unit/integration test structure
- [x] Add GitHub Actions for hardware-independent checks

## Phase 2 — Native UI redesign

- [x] Replace the Tkinter application shell with PySide6/Qt
- [x] Add modern application shell and sidebar navigation
- [x] Complete Dictate page with waveform, microphone state, selected language, active text mode, device and model status
- [x] Add Notes page
- [x] Add History page
- [x] Add Vocabulary page
- [ ] Add Analytics page
- [x] Redesign Settings into focused categories
- [ ] Add first-run onboarding
- [x] Add modern recording/transcribing overlay
- [ ] Add tray integration and minimize-to-tray behavior
- [x] Add scalable theme foundation
- [ ] Validate global hotkeys and paste-to-cursor behavior end-to-end on Windows

## Phase 3 — Dictation intelligence

- [x] Add Verbatim mode
- [x] Add Smart Dictation mode
- [ ] Add Notes-specific structural formatting
- [x] Preserve literal/raw transcript separately from transformed transcript
- [x] Improve punctuation and sentence segmentation using word timestamps
- [ ] Make cleanup transformations explainable/reversible in the UI
- [x] Add vocabulary profiles
- [ ] Add application-aware vocabulary selection
- [ ] Improve true language identification beyond script-only detection
- [ ] Experiment with code-switched English + Indian-language speech
- [ ] Measure every AI/NLP change against reproducible test audio

## Phase 4 — History, privacy, and productivity

- [x] Searchable local transcript history
- [x] Copy / repaste / edit / delete actions
- [x] Language, application, and date filters
- [x] Export TXT/Markdown
- [x] Add runtime support for private sessions
- [x] Add runtime support for disabling history
- [x] Configurable retention period
- [x] Add clear-history control to the UI
- [x] Local usage analytics (words, utterances, latency, RTF, estimated typing time saved)

## Phase 5 — Reliability and diagnostics

- [x] Microphone input-level diagnostics
- [x] Model/GPU/driver diagnostics
- [ ] CPU/CUDA fallback validation
- [ ] Failure-safe clipboard and focus handling validation
- [x] Crash-safe settings writes
- [x] Performance benchmark recording command
- [ ] Expanded multilingual test corpus
- [x] Regression tests for cleanup modes and script/language presentation
- [ ] Windows 10/11 compatibility checks

## Phase 6 — Distribution

- [ ] Package EchoType as a Windows executable
- [ ] Build installer
- [ ] First-run model download with progress/retry/resume
- [ ] GitHub Releases
- [x] Versioned changelog
- [x] Release notes
- [ ] Screenshots and demo video/GIF
- [ ] Architecture diagram
- [ ] Benchmark documentation
- [x] Public beta README

## Release principle

**Quality > quantity.**

A feature is not considered complete until it works end-to-end, has a clear failure mode, preserves user privacy expectations, and does not regress the core dictation workflow.

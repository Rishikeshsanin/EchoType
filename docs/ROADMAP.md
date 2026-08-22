# EchoType V2 Roadmap

EchoType will be upgraded in stages so the working offline dictation pipeline remains recoverable while the application is redesigned.

> **Current checkpoint:** the V2 Dictate engine is implemented on `develop` and tracked in draft PR #1. Hardware-dependent microphone/model/CUDA validation is still required before it can merge to `main`.

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
- [ ] Add structured logging and a diagnostics report
- [x] Define a validated settings schema with atomic persistence
- [x] Add pytest unit/integration test structure
- [x] Add GitHub Actions for hardware-independent checks

## Phase 2 — Native UI redesign

- [x] Replace the Tkinter application shell with PySide6/Qt
- [x] Add modern application shell and sidebar navigation
- [ ] Complete Dictate page with waveform, microphone state, selected language, active text mode, device and model status
- [ ] Add Notes page
- [ ] Add History page
- [ ] Add Vocabulary page
- [ ] Add Analytics page
- [ ] Redesign Settings into focused categories
- [ ] Add first-run onboarding
- [ ] Add modern recording/transcribing overlay
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
- [x] Add runtime support for private sessions
- [x] Add runtime support for disabling history
- [ ] Configurable retention period
- [ ] Add clear-history control to the UI
- [ ] Local usage analytics (words, utterances, latency, RTF, estimated typing time saved)

## Phase 5 — Reliability and diagnostics

- [ ] Microphone test and input-level diagnostics
- [ ] Model/GPU/driver diagnostics
- [ ] CPU/CUDA fallback validation
- [ ] Failure-safe clipboard and focus handling validation
- [x] Crash-safe settings writes
- [ ] Performance benchmark command
- [ ] Expanded multilingual test corpus
- [x] Regression tests for cleanup modes and script/language presentation
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

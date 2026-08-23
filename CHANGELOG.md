# Changelog

All notable user-facing changes to EchoType are recorded here.

## [0.9.0-beta] - Unreleased

### Added

- New native PySide6 desktop interface for Windows
- Complete searchable multilingual language selector with popular-language grouping
- Verbatim, Smart, and Notes output modes
- No-focus recording/transcribing overlay
- Local transcript History with search, filters, edit, export, delete, and repaste
- Persistent Notes with autosave, search, copy, export, and transcript intake
- Vocabulary profiles with preferred spellings and aliases
- Categorized Audio, Language, Dictation, Shortcut, Compute, Privacy, Appearance, and Diagnostics settings
- Local diagnostics and per-session dictation metrics
- Dark, light, and system themes

### Improved

- System-wide push-to-talk, toggle dictation, cancellation, and paste-last behavior
- Immediate capture-buffer closure and listening-state reset on push-to-talk release
- Responsive input voice spikes with quiet, voice, clipping, and ambient-only states
- Multilingual and Indic typography
- Privacy storage under the per-user application-data directory
- Truthful language/script presentation that does not equate script detection with language ID
- Model revision security and cached/offline revision recovery
- Recording feedback and previous-transcript presentation during new processing
- Captured-window delivery, focus restoration, and target-application naming
- Configured shortcuts presented as readable keycaps

### Fixed

- Generic Python and ApplicationFrameHost process names overriding recognizable target titles
- Ambient microphone telemetry appearing to be continued recording after release
- Repeated Right Shift release paths attempting to stop the same utterance more than once
- Microphone callback samples being insufficiently documented/tested at the utterance-close boundary
- Language changes during processing relabeling an in-flight transcript with the new selection
- Invalid typed language searches disturbing the last valid selection
- Previous transcript metadata appearing to describe an in-progress utterance
- Product footer confusing reference-project authorship with EchoType development

### Security

- Immutable commit revisions are required for model repositories that execute remote model code
- Diagnostic output redacts common credential patterns and user-home paths
- Conservative blocking prevents paste-back into detectable standard Windows password controls

### Known limitations

- Recognition accuracy improvements and measured multilingual benchmarks are ongoing
- True language identification and robust code-switched dictation are not implemented
- Browser and application custom password fields cannot always be identified
- Advanced Notes intelligence and automatic structuring are not yet implemented
- Windows packaging, signing, and an installer are not included in this source beta
- Final real-device release validation is still required before tagging or publishing

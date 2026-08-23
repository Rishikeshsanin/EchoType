# EchoType v0.9.0 Beta release checklist

**Publication status: BLOCKED PENDING FINAL MANUAL WINDOWS VALIDATION.**

This branch may be merged, tagged, or published only after every required manual item below is
explicitly completed by the user. A clean diff, green tests, or this document alone does not authorize
release publication.

Planned publication tag: `v0.9.0-beta`

## Source and release preparation

- [x] Release branch starts from verified candidate commit `195f72930c345275a8dd1d92cc571dfaf24e4db6`
- [x] Release branch is `codex/v0.9-release`, not `develop` or `main`
- [x] Package version is defined authoritatively as `0.9.0`
- [x] README, changelog, release notes, attribution, and known limitations are prepared
- [x] Sharadh Naidu / `SharadhNaidu/srivaani-demo` reference attribution is preserved
- [x] ARTPARK-IISc / SraVaani-1.0 model attribution is preserved
- [ ] Record exact resolved mirror and upstream immutable model revisions from the test device
- [ ] Confirm final source commit and attach it to the manual test record

## Automated gate

- [x] `git diff --check`
- [x] `python -m compileall -q src tests benchmarks verify.py`
- [x] `python -m pytest -q` — 142 passed on the release-preparation environment
- [x] fatal Ruff checks: `E9,F63,F7,F82`
- [x] `python verify.py`
- [x] Qt offscreen smoke at 940×640, 1280×800, 1366×768, and 1600×900
- [x] Dark, light, and system theme construction smoke
- [x] Actual application startup smoke with Hugging Face/Transformers forced offline
- [x] Working tree clean after the release-preparation commit

The automated items above were updated from the final validation run on this branch. They do not
replace the unchecked real-device tests below.

## Required manual language validation

For each language, confirm readable UI text, correct manual selection, expected script, transcript
replacement, Unicode copy, and Unicode paste-back. Auto-detect is script evidence, not proof of
spoken language.

- [ ] English dictation (Auto-detect and English selected)
- [ ] Telugu dictation (Auto-detect and Telugu selected)
- [ ] Kannada dictation (Auto-detect and Kannada selected)
- [ ] Hindi / Devanagari dictation (Auto-detect and Hindi selected)
- [ ] Tamil dictation (Auto-detect and Tamil selected)

## Required manual shortcut and recording validation

- [ ] Right Shift starts Listening exactly once and release stops Listening immediately
- [ ] Right Shift release produces no audible/visible capture tail in the completed utterance
- [ ] Very fast Right Shift tap reports too short without transcript, history, copy, or paste
- [ ] Right Shift auto-repeat does not restart recording
- [ ] Repeated Right Shift press/release does not duplicate transcription or paste
- [ ] Right Shift + F9 interaction stops/submits at most once
- [ ] F9 starts toggle dictation and a second F9 stops it
- [ ] F11 pastes the last successful transcript once while idle
- [ ] Esc while Listening cancels with no submission, transcript, history, copy, or paste
- [ ] Esc near Right Shift release never duplicates submission or leaves a stale overlay
- [ ] Silence produces no transcript, history, copy, or paste
- [ ] Microphone unavailable/disconnect fails clearly and recovers safely where testable

## Required manual Windows target validation

### Notepad

- [ ] Paste into Notepad at the captured caret
- [ ] Overlay target displays `Notepad`, never `Python`
- [ ] Unicode Indic text remains intact
- [ ] Start in Notepad, switch windows during recording, and confirm the captured-target policy

### Chrome

- [ ] Paste into a normal Chrome textarea at the captured caret
- [ ] Overlay target displays `Google Chrome`
- [ ] A detectable password field is blocked
- [ ] Acknowledge that custom browser password fields cannot always be identified

### Visual Studio Code

- [ ] Paste into VS Code at the captured caret
- [ ] Overlay target displays `Visual Studio Code`, never `Python`
- [ ] Unicode Indic text remains intact

### Focus safety

- [ ] EchoType and its overlay never become an external paste target
- [ ] Closing the captured app preserves the transcript and does not paste elsewhere
- [ ] Switching to EchoType before release still follows the recorded target policy
- [ ] Failed focus restoration leaves the transcript available and reports the failure

## Required manual feature validation

- [ ] Copy latest transcript
- [ ] Clear latest transcript without deleting History
- [ ] Send to Notes exactly once and preserve Unicode
- [ ] Notes create/open/autosave/search/copy/export
- [ ] History newest-first/search/filter/edit/export/delete/repaste
- [ ] History disabled persists nothing after restart
- [ ] Private mode persists nothing after restart while dictation and paste still work
- [ ] Vocabulary profile create/edit/activate/persist and Smart replacement
- [ ] Settings persist language, shortcuts, microphone, privacy, compute, and theme
- [ ] Duplicate shortcut assignments are rejected clearly
- [ ] Language search rejects invalid text and preserves the prior selection
- [ ] Language selection made during processing applies to the next utterance only

## Required manual compute, theme, and layout validation

- [ ] CUDA / FP16 reports and uses the actual NVIDIA device
- [ ] CPU / FP32 path completes a live dictation
- [ ] CUDA failure falls back explicitly to CPU / FP32
- [ ] Dark theme at 940×640, 1280×800, 1366×768, and 1600×900
- [ ] Light theme at 940×640, 1280×800, 1366×768, and 1600×900
- [ ] System theme follows Windows appearance
- [ ] Windows DPI scaling at 100%, 125%, and 150% where practical
- [ ] No clipping, black QLabel rectangles, unreadable Indic text, or unreachable controls
- [ ] Ready, Listening, Transcribing, loading, error, cancelled, and success states
- [ ] Input bars respond to speech, show quiet/clipping states, and reset immediately on release
- [ ] Previous transcript is unmistakable while a new utterance is processing

## Stop-ship conditions

- Wrong-window paste, duplicate paste, transcript loss, or clipboard corruption
- Any completed-utterance samples appended after push-to-talk release
- Listening waveform/timer continuing after release
- Private-session or history-disabled transcript persistence
- Esc, silence, too-short, or failed jobs causing copy, paste, or persistence
- CUDA state falsely reported after CPU fallback
- Unpinned execution of model-provided remote code
- Indic Unicode corruption in a supported target application
- EchoType/overlay captured as the external paste target
- Missing attribution, committed credentials, private audio, or private runtime data

## Final publication actions — do not perform yet

- [ ] User explicitly approves the completed manual matrix
- [ ] Merge the validated release commit into `main`
- [ ] Create annotated tag `v0.9.0-beta`
- [ ] Publish the GitHub Release using `docs/RELEASE_NOTES_0.9.0.md`
- [ ] Confirm the public README, changelog, release notes, tag, and attached artifacts

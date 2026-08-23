# Manual hardware QA checklist

Do not mark v1.0 ready from unit tests alone. Run this checklist on real Windows machines and attach
logs/screenshots plus `benchmark-results.jsonl` to the release evidence.

## Test record

- [ ] EchoType commit and model repository/revision recorded
- [ ] Windows edition/version/build recorded (Windows 10 or Windows 11)
- [ ] CPU, RAM, microphone, and target-app versions recorded
- [ ] GPU/driver/CUDA/PyTorch versions recorded when applicable
- [ ] Fresh application-data run and existing-settings upgrade run both covered
- [ ] No transcript contains secrets or unrelated private speech in attached evidence

## CPU smoke gate

- [ ] Force **CPU** and restart; ready state reports `CPU / FP32`
- [ ] First model load completes; second launch uses cached model successfully
- [ ] Hold Right Shift, dictate a sentence, release, and receive one transcript
- [ ] Transcript pastes at the original caret without duplicated text
- [ ] No model download starts during the warm-cache/offline launch

## CUDA smoke gate

- [ ] Select **CUDA** and restart; actual selected device is CUDA
- [ ] Ready state reports `CUDA / FP16` when FP16 is configured and supported
- [ ] Transcription completes and output matches the spoken language/script
- [ ] Record device, precision, transcription duration, audio duration, and RTF
- [ ] If CUDA is unavailable/broken, fallback is explicit and reports `CPU / FP32` rather than a false CUDA state

## Target application matrix

Repeat basic dictate and paste-back in each target:

- [ ] Windows Notepad
- [ ] Chrome normal textbox/textarea (not a password field)
- [ ] VS Code or another desktop editor

For each app:

- [ ] Start with the caret in the middle of existing text; paste occurs at that caret
- [ ] Unicode Indic text is intact
- [ ] F11 pastes the last transcript again without retranscribing
- [ ] Copy works with auto-paste off
- [ ] EchoType/overlay never becomes the paste target

## Language matrix

Run every row with **Auto-detect** and with the matching **manual language lock**.

| Language | Expected script | Auto short | Auto long | Manual short | Manual long | Noisy |
|---|---|---:|---:|---:|---:|---:|
| English | Latin | [ ] | [ ] | [ ] | [ ] | [ ] |
| Telugu | Telugu | [ ] | [ ] | [ ] | [ ] | [ ] |
| Hindi | Devanagari | [ ] | [ ] | [ ] | [ ] | [ ] |
| Kannada | Kannada | [ ] | [ ] | [ ] | [ ] | [ ] |
| Tamil | Tamil | [ ] | [ ] | [ ] | [ ] | [ ] |

For every cell, verify transcript readability, pasted Unicode, selected language, detected script,
script mismatch warning, audio duration, processing duration, RTF, word count, SNR, device, and precision.
Shared scripts must be described as script evidence, not certain language identification.

## Recording, noise, and cancellation

- [ ] Short utterance after a longer same-language sentence inherits the session script
- [ ] Two consecutive strong contrary-script utterances can switch the Auto session prior
- [ ] Quiet room produces a transcript without unnecessary degradation
- [ ] Noisy room reports SNR and still produces useful text; record failure honestly
- [ ] Silence produces no transcript, no history entry, no clipboard change, and no paste
- [ ] Very short clip is reported as too short and causes no paste
- [ ] Esc during recording cancels: no model submission, transcript, history, copy, or paste
- [ ] Right Shift press/release starts/stops once even with key-repeat
- [ ] F9 starts a toggle recording; F9 again stops it
- [ ] F11 while idle repastes the last successful transcript

## Focus switching and overlay

- [ ] Start recording in Notepad, switch to EchoType before release: result returns to Notepad
- [ ] Start recording in Chrome, switch to VS Code before release: captured-target policy is clear and consistent
- [ ] Close the target app before transcription completes: transcript remains available and no wrong app receives it
- [ ] Minimized target restoration either succeeds or fails safely with transcript retained on clipboard
- [ ] Overlay shows listening, processing, cancelled, empty/no-speech, and ready transitions
- [ ] Overlay does not take keyboard focus and cannot be captured as an external target
- [ ] Input meter responds to speech and remains visually bounded for loud input

## Privacy, persistence, and recovery

- [ ] History enabled/private off persists one successful transcript
- [ ] History disabled persists nothing across restart
- [ ] Private session persists nothing across restart while dictation/paste still works
- [ ] Esc, silence, too-short, and failed jobs never persist history
- [ ] Clear/delete behavior affects only the explicitly selected scope
- [ ] Settings, custom vocabulary, language, and shortcuts persist after restart
- [ ] Corrupt settings/history do not block launch; recovery does not expose raw secrets
- [ ] Runtime data is under `%LOCALAPPDATA%\EchoType`, not the Git checkout

## Notes/history/settings acceptance

- [ ] Copy, paste last, send to note, and clear act exactly once
- [ ] History is newest-first; search/filter/export/delete do not change unrelated entries
- [ ] Send to note and direct note dictation do not paste into another app
- [ ] Note new/open/save/copy and optional timestamps preserve Unicode
- [ ] Vocabulary save/reload works; Smart applies terms and Verbatim does not rewrite them
- [ ] Hotkey changes refresh active bindings and duplicate bindings are rejected or clearly handled

## Benchmark evidence

Use `benchmarks/record_result.py` and the method in `benchmarks/README.md`. Record measured values only:

- [ ] transcription duration
- [ ] audio duration
- [ ] RTF
- [ ] words
- [ ] device and precision
- [ ] SNR
- [ ] selected language and detected script
- [ ] case ID, Windows version, target app, cleanup mode, model revision, and relevant notes

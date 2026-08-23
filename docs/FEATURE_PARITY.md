# EchoType feature parity audit

This is developer/release evidence, not a product-completeness claim.

Audit snapshot:

- EchoType `develop`: `ec1205a120041e932884cedf9b04e7ce05302aa6`
- Reference: [`SharadhNaidu/srivaani-demo`](https://github.com/SharadhNaidu/srivaani-demo) at
  `e422746692c0cf19e6e272d380d1d1df8576ea54`
- Audit date: 2026-08-23

The reference application remains the minimum useful behavior baseline. “Implemented” below means a
code path exists; it does not replace the Windows hardware checks in `QA_CHECKLIST.md`.

Status terms: **yes** = present and connected, **partial** = service/core exists but user flow or
evidence is incomplete, **missing** = no working equivalent on the audited commit.

| Capability | Reference behavior | EchoType `develop` | Release acceptance / current gap |
|---|---|---|---|
| Model load/status | Async load; ready/busy/failed UI | **Yes**; async engine and status chip | Fresh-cache and warm-cache load must pass on Windows; failure copy must be actionable. |
| CPU/CUDA | Auto/CPU/CUDA selection with CPU fallback | **Yes** in engine; **partial** UI configuration | Verify explicit CPU, explicit CUDA, auto, and unavailable-CUDA fallback. Settings UI is pending. |
| FP16/FP32 | FP16 on CUDA, FP32 on CPU | **Yes** | UI must report actual post-fallback precision. CPU+FP16 must never be reported. |
| Microphone capture | 16 kHz mono, 400 ms pre-roll, always-open stream | **Yes** | Verify first word is not clipped and selected/default device works. |
| Noise reduction | SNR-adaptive spectral gate | **Yes** in audio core | Settings UI pending; noisy-room machine evidence required. |
| VAD | WebRTC trimming plus speech gate | **Yes** | Silence must produce no transcript/paste; very short speech must not crash. |
| SNR | Estimated and shown with transcript | **Partial**; calculated and emitted in metadata, not shown in audited UI | Show/log measured SNR and preserve it in history/benchmark evidence. |
| Auto gain | Quiet-input gain with clipping guard | **Yes** in audio core | Settings UI pending; quiet-mic manual check required. |
| Language list | Auto plus scheduled/extended language list | **Partial**; list exists in `core/languages.py`, no selector in audited UI | Language selector must expose at least English, Telugu, Hindi, Kannada, Tamil and Auto. |
| Auto language/script behavior | Free decode; sticky session script for short utterances | **Yes** in decoder/engine; metadata not surfaced | Long utterance establishes script prior; short utterance inherits; two contrary observations switch it. |
| Manual language selection | Decoder token mask locks selected script | **Partial**; setting and mask exist, no audited UI control | Selecting a language must reset session memory and visibly show the lock. |
| Indic scripts | Devanagari, Bengali, Kannada, Telugu, Tamil, Malayalam, Gujarati, Gurmukhi, Odia, Ol Chiki | **Yes** in metadata/masking core | Render and paste Unicode correctly in all three target apps; mandatory five-language set is in QA checklist. |
| Push-to-talk | Hold configured key, release to transcribe | **Yes** | Default Right Shift and rebind behavior require global-hook machine test. |
| F9 | Toggle long-form recording | **Yes** in hotkey/runtime | Direct unit logic passes; global hook and toggle state require machine test. |
| F11 | Paste last transcript | **Yes** in hotkey/runtime | Must repaste to the intended last target without retranscription. |
| Esc | Cancel active recording | **Yes** | Must not submit, persist, copy, or paste the cancelled clip. |
| Active-window capture | Captures HWND/title/PID when recording starts | **Yes** | Switching apps while recording must still deliver to the captured target. |
| Paste-back | Restore target, verified clipboard, Ctrl+V, typed fallback | **Yes** | Notepad, Chrome textbox, and VS Code/editor must pass on Windows 10/11. |
| Recording overlay | Floating listening/transcribing/cancelled pill with level | **Missing** on audited commit | Overlay agent owns implementation; it must not steal focus or become paste target. |
| Input level | Live sidebar meter and overlay waveform | **Partial**; audio engine exposes level/waveform, UI absent | Meter must respond without recording and remain bounded under clipping. |
| Transcript | Latest transcript visible | **Yes** | Raw and cleaned text must remain distinguishable for Verbatim QA. |
| Transcript metadata | Time, RTF, words, SNR, language/script, target/device | **Partial**; runtime calculates most fields; UI shows mode/RTF/device only; words and language/script absent | Required fields: duration, audio duration, RTF, words, device, precision, SNR, selected language, detected script, target, mode. |
| Copy | Manual copy of latest transcript | **Partial**; automatic clipboard delivery exists, manual action absent | Manual copy must work even when auto-paste is disabled. |
| Paste last | Button and F11 | **Partial**; F11/runtime path exists, button absent | Both entry points must reuse text and target safely. |
| Send to notes | Append latest transcript to note | **Missing** on audited commit | Must append exactly once, respect timestamp option, and avoid external paste. |
| Clear | Clear latest transcript UI | **Missing** on audited commit | Must not silently erase persisted history unless explicitly requested. |
| History | Session list and persisted local history | **Partial**; append/read/clear store exists, page is placeholder | History agent owns UI. Privacy-off/private-session behavior must remain enforced. |
| Notes | Editable note, direct dictation, save/open/copy/new | **Missing**; Notes mode label exists but processing matches Smart and page is placeholder | Do not describe Notes as complete until file and direct-dictation flows pass. |
| Settings | Audio/output/shortcut/compute controls | **Partial**; persisted service exists, page is placeholder | Settings agent owns UI. Restart-required compute behavior must be explicit. |
| Custom vocabulary | One term per line, persisted, used in cleanup | **Partial**; defaults and cleanup exist, editor/profile UI absent | Save/reload and literal Verbatim non-interference must pass. |
| Session metrics | Words, count, average RTF, estimated time saved | **Partial**; per-result values exist, no audited session aggregation/UI | Never invent values; aggregate only completed successful transcripts and define reset scope. |

## Important behavior differences

- EchoType intentionally distinguishes detected **script evidence** from true language identification.
  A Devanagari result is not proof of Hindi. Shared-script output must be labeled as a hint.
- Verbatim mode is an EchoType behavior contract: only decoder whitespace normalization is allowed.
  Spoken-punctuation conversion, vocabulary rewrites, filler removal, contractions, and compound edits
  are forbidden in this mode.
- The audited EchoType revision persists cleaned text **and raw decoder text** as plaintext JSONL under
  the user’s local application-data directory. This is local, not encrypted storage.
- The reference UI is more functionally complete than the audited EchoType shell. Modern styling does
  not count as parity for missing Notes, History, Settings, overlay, or action flows.

## Security parity notes

- EchoType reads Hugging Face credentials from environment variables only; no committed credential
  patterns or tracked runtime settings/history/log files were found in this audit.
- Model remote code is enabled. The mirror revision is resolved to and persisted as an immutable SHA,
  and malformed stored revisions are now rejected by unit-tested helper logic.
- **Open blocker:** the upstream fallback does not yet persist/pass its own immutable revision. A
  release should either pin every remote-code repository in source or persist a per-repository SHA and
  refuse unpinned remote code.
- Focus capture records the top-level window, not the focused control type. EchoType therefore cannot
  currently prove that a paste target is not a password/secret field; release UX and safety policy for
  sensitive controls remains open.
- Model files remain in the Hugging Face cache; settings/history live outside the repository. See
  `ARCHITECTURE.md` for paths and trust boundaries.

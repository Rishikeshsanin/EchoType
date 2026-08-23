# Release checklist

No checked-in document or green CI run by itself authorizes a v1.0 claim.

## Source and integration

- [ ] Integrate from `develop`; do not merge QA work directly to `main`
- [ ] Preserve the SraVaani-demo and ARTPARK-IISc attribution in README/NOTICE
- [ ] Merge feature branches in the recommended order and resolve behavior, not just text conflicts
- [ ] Re-run feature parity audit against the integration commit
- [ ] Confirm no placeholders remain for features represented as complete
- [ ] Record exact model repository and immutable revision(s)

## Automated gate

- [ ] Python 3.11 Windows CI passes compile, lint, and full unit suite
- [ ] Python 3.12 Windows CI passes compile, lint, and full unit suite
- [ ] Cross-platform syntax parse passes
- [ ] CI logs show no model download and require no GPU/audio/global keyboard hook
- [ ] No committed `.env`, token, settings, history, logs, caches, models, benchmark results, or private audio
- [ ] Dependency and installer changes have been reviewed separately from application code

## v0.9 preview gate

- [ ] Integrated Dictate/UI, overlay, History/Notes, Settings/Vocabulary branches compile together
- [ ] One real Windows 10 or 11 CPU machine passes the CPU smoke gate
- [ ] Notepad, Chrome textbox, and VS Code/editor paste-back pass
- [ ] English plus at least Telugu, Hindi, Kannada, and Tamil manual checks are recorded
- [ ] Privacy controls and Esc/silence/too-short non-persistence pass
- [ ] Known parity gaps and preview limitations are published; v0.9 is labeled pre-release

## v1.0 gate

- [ ] Full `QA_CHECKLIST.md` passes on both Windows 10 and Windows 11
- [ ] CPU and NVIDIA CUDA/FP16 paths pass on real supported hardware
- [ ] Fresh install, first model fetch, cached/offline restart, upgrade, and uninstall/data-retention behavior pass
- [ ] Every `trust_remote_code=True` source is pinned to an immutable reviewed revision
- [ ] Required apps/languages/short-long/noisy/silence/hotkey/focus-switch cases have evidence
- [ ] Benchmark JSONL contains measured runs only; no performance number is claimed without its source runs
- [ ] Accessibility, scaling, small-screen layout, crash recovery, and signed/package distribution checks pass
- [ ] Release notes accurately distinguish script hints from language identification
- [ ] Maintainer explicitly approves promotion from `develop`; only then may a release merge target `main`

## Stop-ship conditions

- Wrong-window paste, password-field ambiguity, transcript loss, duplicate paste, or clipboard corruption
- Private-session/history-disabled transcript persistence
- Esc/silence/too-short clip causing paste or persistence
- CUDA state falsely reported after CPU fallback
- Unpinned execution of model-provided remote code
- Indic Unicode corruption in a supported target app
- Missing attribution or committed credentials/private runtime data

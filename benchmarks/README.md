# Lightweight transcription benchmark

This recorder stores measured metadata; it does not run or download a speech model and it does not
contain invented performance numbers.

For each manual test clip, record the audio duration shown by EchoType and measure transcription time
from release of the recording key until the transcript is ready. Count words using the text EchoType
actually emitted. Record the UI-reported device, precision, SNR, language, and script.

```powershell
python benchmarks/record_result.py `
  --case-id en-notepad-long-01 `
  --transcription-seconds <MEASURED_SECONDS> `
  --audio-seconds <AUDIO_SECONDS> `
  --words <WORD_COUNT> `
  --device cpu `
  --precision fp32 `
  --snr-db <REPORTED_SNR> `
  --language English `
  --script Latin `
  --windows 11 `
  --target-app Notepad
```

The tool calculates `rtf = transcription_seconds / audio_seconds` and appends one JSON object to
`benchmark-results.jsonl`. Run each case at least three times after model warm-up. Keep raw per-run
records; summarize medians only after preserving failures and outliers with notes.

Use stable case IDs for the CPU/CUDA, language, short/long utterance, and quiet/noisy scenarios in
`docs/QA_CHECKLIST.md`. Do not compare runs from different audio, model revisions, or cleanup modes as
if they were equivalent.

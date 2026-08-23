from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from echotype.core.metrics import calculate_metrics


def build_record(args: argparse.Namespace) -> dict[str, object]:
    record = calculate_metrics(
        transcription_seconds=args.transcription_seconds,
        audio_seconds=args.audio_seconds,
        words=args.words,
        device=args.device,
        precision=args.precision,
        snr_db=args.snr_db,
        language=args.language,
        script=args.script,
    ).as_dict()
    record.update(
        {
            "recorded_at": datetime.now(UTC).isoformat(),
            "case_id": args.case_id,
            "windows": args.windows,
            "target_app": args.target_app,
            "mode": args.mode,
            "notes": args.notes,
        }
    )
    return record


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Record one measured EchoType transcription benchmark as JSONL."
    )
    result.add_argument("--case-id", required=True)
    result.add_argument("--transcription-seconds", required=True, type=float)
    result.add_argument("--audio-seconds", required=True, type=float)
    result.add_argument("--words", required=True, type=int)
    result.add_argument("--device", required=True, choices=("cpu", "cuda"))
    result.add_argument("--precision", required=True, choices=("fp16", "fp32"))
    result.add_argument("--snr-db", type=float)
    result.add_argument("--language", required=True)
    result.add_argument("--script", required=True)
    result.add_argument("--windows", choices=("10", "11"), default="11")
    result.add_argument("--target-app", default="Notepad")
    result.add_argument("--mode", choices=("verbatim", "smart", "notes"), default="smart")
    result.add_argument("--notes", default="")
    result.add_argument("--output", type=Path, default=Path("benchmark-results.jsonl"))
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        record = build_record(args)
    except ValueError as exc:
        parser().error(str(exc))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

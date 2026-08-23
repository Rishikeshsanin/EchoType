from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.record_result import main
from echotype.core.metrics import calculate_metrics


def test_transcript_metric_calculations() -> None:
    metrics = calculate_metrics(
        transcription_seconds=1.25,
        audio_seconds=5.0,
        words=12,
        device="CUDA",
        precision="FP16",
        snr_db=18.5,
        language="Telugu",
        script="Telugu",
    )
    assert metrics.rtf == pytest.approx(0.25)
    assert metrics.words == 12
    assert metrics.device == "cuda"
    assert metrics.precision == "fp16"
    assert metrics.snr_db == pytest.approx(18.5)
    assert metrics.language == "Telugu"
    assert metrics.script == "Telugu"


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "transcription_seconds": -1,
            "audio_seconds": 1,
            "words": 1,
            "device": "cpu",
            "precision": "fp32",
        },
        {
            "transcription_seconds": 1,
            "audio_seconds": 0,
            "words": 1,
            "device": "cpu",
            "precision": "fp32",
        },
        {
            "transcription_seconds": 1,
            "audio_seconds": 1,
            "words": -1,
            "device": "cpu",
            "precision": "fp32",
        },
        {
            "transcription_seconds": 1,
            "audio_seconds": 1,
            "words": 1,
            "device": "cpu",
            "precision": "fp16",
        },
    ],
)
def test_invalid_benchmark_measurements_are_rejected(kwargs) -> None:
    with pytest.raises(ValueError):
        calculate_metrics(**kwargs)


def test_benchmark_recorder_appends_machine_readable_jsonl(tmp_path: Path) -> None:
    output = tmp_path / "runs.jsonl"
    argv = [
        "--case-id",
        "en-notepad-long-01",
        "--transcription-seconds",
        "2.0",
        "--audio-seconds",
        "8.0",
        "--words",
        "14",
        "--device",
        "cpu",
        "--precision",
        "fp32",
        "--snr-db",
        "20",
        "--language",
        "English",
        "--script",
        "Latin",
        "--output",
        str(output),
    ]
    assert main(argv) == 0
    assert main(argv) == 0

    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 2
    assert records[0]["case_id"] == "en-notepad-long-01"
    assert records[0]["rtf"] == pytest.approx(0.25)
    assert records[0]["device"] == "cpu"

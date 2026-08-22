from __future__ import annotations

import ast
from pathlib import Path

import echotype


ROOT = Path(__file__).resolve().parents[1]


def test_version_is_defined() -> None:
    assert echotype.__version__


def test_python_sources_parse() -> None:
    for path in (ROOT / "src").rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

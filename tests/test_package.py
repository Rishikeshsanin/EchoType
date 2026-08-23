from __future__ import annotations

import ast
import importlib
from pathlib import Path

import echotype

ROOT = Path(__file__).resolve().parents[1]


def test_version_is_defined() -> None:
    assert echotype.__version__ == "0.9.0"


def test_python_sources_parse() -> None:
    sources = list((ROOT / "src").rglob("*.py"))
    sources.extend((ROOT / "benchmarks").rglob("*.py"))
    sources.append(ROOT / "verify.py")
    for path in sources:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_hardware_independent_modules_import_without_runtime_services() -> None:
    modules = (
        "echotype",
        "echotype.core.cleanup",
        "echotype.core.language_session",
        "echotype.core.languages",
        "echotype.core.metrics",
        "echotype.services.diagnostics",
        "echotype.services.history",
        "echotype.services.injection",
        "echotype.services.model_revision",
        "echotype.services.settings",
    )
    for module in modules:
        assert importlib.import_module(module)

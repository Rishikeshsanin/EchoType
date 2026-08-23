from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from echotype.core.cleanup import SMART, clean
from echotype.core.transcription import Job, TranscriptionEngine
from echotype.services.diagnostics import DiagnosticsService, sanitize_diagnostics
from echotype.services.settings import DEFAULTS, Settings
from echotype.services.vocabulary import VocabularyService


def test_invalid_persisted_settings_fall_back_independently(tmp_path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "language": "not-a-language",
                "device": "quantum",
                "denoise_strength": 4.2,
                "auto_gain": False,
                "history_retention_days": -10,
            }
        ),
        encoding="utf-8",
    )

    settings = Settings(path)

    assert settings.get("language") == DEFAULTS["language"]
    assert settings.get("device") == DEFAULTS["device"]
    assert settings.get("denoise_strength") == DEFAULTS["denoise_strength"]
    assert settings.get("history_retention_days") == 0
    assert settings.get("auto_gain") is False


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("device", "metal"),
        ("precision", "int8"),
        ("denoise_strength", 1.1),
        ("history_enabled", "yes"),
        ("hotkey_toggle", "ctrl+shift+x"),
        ("language", "xx-invalid"),
    ],
)
def test_settings_reject_invalid_values(tmp_path, key, value) -> None:
    settings = Settings(tmp_path / "settings.json")
    with pytest.raises(ValueError):
        settings.set(key, value)


def test_settings_update_is_atomic_when_one_value_is_invalid(tmp_path) -> None:
    settings = Settings(tmp_path / "settings.json")
    before = settings.as_dict()
    with pytest.raises(ValueError):
        settings.update({"auto_gain": False, "device": "invalid"})
    assert settings.as_dict() == before
    assert not settings.path.exists()


def test_vocabulary_profile_and_term_crud_persists(tmp_path) -> None:
    path = tmp_path / "vocabulary.json"
    service = VocabularyService(path)

    profile = service.create_profile("Client Alpha")
    service.rename_profile(profile["id"], "Client Platform")
    service.activate_profile(profile["id"])
    term = service.add_term(profile["id"], "Supabase", ["supa base"])
    service.edit_term(profile["id"], term["id"], "Supabase", ["supa base", "super base"])

    loaded = VocabularyService(path)
    assert loaded.active_profile_id == profile["id"]
    assert loaded.get_profile(profile["id"])["name"] == "Client Platform"
    assert loaded.search("super", profile["id"])[0]["term"] == "Supabase"

    loaded.delete_term(profile["id"], term["id"])
    assert loaded.get_profile(profile["id"])["terms"] == []
    loaded.delete_profile(profile["id"])
    assert loaded.active_profile_id == "general"
    assert all(item["id"] != profile["id"] for item in loaded.profiles())


def test_vocabulary_rejects_duplicates_and_keeps_one_profile(tmp_path) -> None:
    service = VocabularyService(tmp_path / "vocabulary.json")
    with pytest.raises(ValueError):
        service.create_profile("general")

    profile = service.create_profile("Temporary")
    service.add_term(profile["id"], "FastAPI")
    with pytest.raises(ValueError):
        service.add_term(profile["id"], "fastapi")

    for item in list(service.profiles()):
        if item["id"] != profile["id"]:
            service.delete_profile(item["id"])
    with pytest.raises(ValueError):
        service.delete_profile(profile["id"])


def test_active_vocabulary_alias_is_applied_to_cleanup(tmp_path) -> None:
    service = VocabularyService(tmp_path / "vocabulary.json")
    profile = service.create_profile("API work")
    service.add_term(profile["id"], "FastAPI", ["fast a p i", "fast api"])
    service.activate_profile(profile["id"])

    assert service.apply("build it with fast a p i") == "build it with FastAPI"
    result = clean("use fast api comma please", mode=SMART, vocabulary=service.active_terms())
    assert result.text == "Use FastAPI, please"


def test_transcription_engine_uses_active_profile_and_cleanup_setting(tmp_path) -> None:
    settings = Settings(tmp_path / "settings.json")
    vocabulary = VocabularyService(tmp_path / "vocabulary.json")
    profile = vocabulary.create_profile("Runtime")
    vocabulary.add_term(profile["id"], "FastAPI", ["fast api"])
    vocabulary.activate_profile(profile["id"])
    results = []
    engine = TranscriptionEngine(settings, on_result=results.append, vocabulary=vocabulary)
    engine._transcribe = lambda _audio: SimpleNamespace(text="use fast api", timestamp={})
    job = Job(np.ones(16_000, dtype=np.float32), {"speech_ratio": 1.0, "seconds": 1.0})

    engine._handle(job)
    assert results[-1].text == "Use FastAPI"

    settings.set("cleanup", False)
    engine._handle(job)
    assert results[-1].text == "use fast api"


def test_legacy_flat_vocabulary_migrates_into_general_profile(tmp_path) -> None:
    service = VocabularyService(
        tmp_path / "vocabulary.json",
        legacy_terms=["CustomProduct", {"term": "NumPy", "aliases": ["num pie"]}],
    )
    terms = {entry["term"]: entry for entry in service.get_profile("general")["terms"]}
    assert "CustomProduct" in terms
    assert terms["NumPy"]["aliases"] == ["num pie"]
    assert service.path.exists()


def test_diagnostics_sanitization_redacts_keys_and_token_values(tmp_path) -> None:
    raw = {
        "HF_TOKEN": "hf_abcdefghijklmnopqrstuvwxyz",
        "nested": {"authorization": "Bearer abc123", "safe": "CPU"},
        "message": "request used hf_1234567890abcdef",
    }
    cleaned = sanitize_diagnostics(raw)
    assert cleaned["HF_TOKEN"] == "[redacted]"
    assert cleaned["nested"]["authorization"] == "[redacted]"
    assert cleaned["nested"]["safe"] == "CPU"
    assert "hf_" not in cleaned["message"]

    report = DiagnosticsService(Settings(tmp_path / "settings.json")).report()
    assert "HF_TOKEN" not in report
    assert "HUGGING_FACE_HUB_TOKEN" not in report
    assert "App version:" in report

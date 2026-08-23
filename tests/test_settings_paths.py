from __future__ import annotations

import json
from pathlib import Path

from echotype.services.settings import DEFAULTS, Settings, _app_data_dir


def test_windows_application_data_path_uses_localappdata(tmp_path: Path) -> None:
    assert _app_data_dir(os_name="nt", environ={"LOCALAPPDATA": str(tmp_path)}) == (
        tmp_path / "EchoType"
    )


def test_non_windows_application_data_path_uses_xdg(tmp_path: Path) -> None:
    assert _app_data_dir(os_name="posix", environ={"XDG_DATA_HOME": str(tmp_path)}) == (
        tmp_path / "echotype"
    )


def test_application_data_paths_have_safe_home_fallbacks(tmp_path: Path) -> None:
    assert _app_data_dir(os_name="nt", environ={}, home=tmp_path) == (
        tmp_path / "AppData" / "Local" / "EchoType"
    )
    assert _app_data_dir(os_name="posix", environ={}, home=tmp_path) == (
        tmp_path / ".local" / "share" / "echotype"
    )


def test_settings_update_persists_multiple_values_atomically(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    settings = Settings(path)
    settings.update({"language": "te", "private_session": True, "device": "cpu"})

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["language"] == "te"
    assert saved["private_session"] is True
    assert saved["device"] == "cpu"
    assert not path.with_suffix(".json.tmp").exists()


def test_corrupt_settings_fall_back_to_independent_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("not-json", encoding="utf-8")
    settings = Settings(path)
    vocabulary = settings.get("vocabulary")
    vocabulary.append("local mutation")

    clean_instance = Settings(tmp_path / "other.json")
    assert clean_instance.get("vocabulary") == DEFAULTS["vocabulary"]


def test_unknown_loaded_keys_are_ignored(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"language":"ta","secret_future_key":"ignored"}', encoding="utf-8")
    settings = Settings(path)
    assert settings.get("language") == "ta"
    assert "secret_future_key" not in settings.as_dict()

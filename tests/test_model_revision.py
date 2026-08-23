from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from echotype.services.model_revision import immutable_revision, resolve_persisted_revision
from echotype.services.settings import Settings

MIRROR = "owner/model-mirror"
SHA = "a" * 40


class FakeSettings:
    def __init__(self, revision=None) -> None:
        self.data = {"model_revision": revision}
        self.writes: list[tuple[str, str]] = []

    def get(self, key: str):
        return self.data.get(key)

    def set(self, key: str, value: str) -> None:
        self.data[key] = value
        self.writes.append((key, value))


def test_valid_persisted_revision_avoids_network_resolution() -> None:
    settings = FakeSettings(SHA.upper())

    def unexpected(_repo: str):
        raise AssertionError("model_info should not be called")

    assert (
        resolve_persisted_revision(MIRROR, settings, pinned_repo=MIRROR, model_info=unexpected)
        == SHA
    )
    assert settings.writes == []


def test_remote_commit_revision_is_normalized_and_persisted() -> None:
    settings = FakeSettings()
    resolved = resolve_persisted_revision(
        MIRROR,
        settings,
        pinned_repo=MIRROR,
        model_info=lambda _repo: SimpleNamespace(sha=SHA.upper()),
    )
    assert resolved == SHA
    assert settings.writes == [("model_revision", SHA)]


def test_model_revision_survives_real_settings_reload(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    settings = Settings(path)
    assert (
        resolve_persisted_revision(
            MIRROR,
            settings,
            pinned_repo=MIRROR,
            model_info=lambda _repo: SimpleNamespace(sha=SHA),
        )
        == SHA
    )
    assert Settings(path).get("model_revision") == SHA


def test_moving_or_malformed_revision_is_not_treated_as_immutable() -> None:
    assert immutable_revision("main") is None
    assert immutable_revision("abc123") is None
    settings = FakeSettings("main")
    assert (
        resolve_persisted_revision(
            MIRROR,
            settings,
            pinned_repo=MIRROR,
            model_info=lambda _repo: SimpleNamespace(sha="also-not-a-sha"),
        )
        is None
    )


def test_unconfigured_fallback_repo_is_not_given_mirror_revision() -> None:
    settings = FakeSettings(SHA)
    assert (
        resolve_persisted_revision(
            "upstream/model",
            settings,
            pinned_repo=MIRROR,
            model_info=lambda _repo: SimpleNamespace(sha=SHA),
        )
        is None
    )


def test_fallback_can_persist_its_own_immutable_revision() -> None:
    settings = FakeSettings()
    settings.data["upstream_model_revision"] = None
    resolved = resolve_persisted_revision(
        "upstream/model",
        settings,
        pinned_repo="upstream/model",
        model_info=lambda _repo: SimpleNamespace(sha=SHA),
        setting_key="upstream_model_revision",
    )
    assert resolved == SHA
    assert settings.writes == [("upstream_model_revision", SHA)]


def test_cached_immutable_revision_is_used_when_network_resolution_fails() -> None:
    settings = FakeSettings()
    resolved = resolve_persisted_revision(
        MIRROR,
        settings,
        pinned_repo=MIRROR,
        model_info=lambda _repo: (_ for _ in ()).throw(OSError("offline")),
        cache_lookup=lambda _repo: SHA,
    )
    assert resolved == SHA
    assert settings.writes == [("model_revision", SHA)]


def test_settings_reject_moving_model_revision(tmp_path: Path) -> None:
    settings = Settings(tmp_path / "settings.json")
    try:
        settings.set("model_revision", "main")
    except ValueError:
        pass
    else:
        raise AssertionError("moving revisions must be rejected")

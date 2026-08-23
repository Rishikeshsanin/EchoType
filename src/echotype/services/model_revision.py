from __future__ import annotations

import re
from collections.abc import Callable

_COMMIT_SHA = re.compile(r"^[0-9a-fA-F]{40,64}$")


def immutable_revision(value: object) -> str | None:
    candidate = str(value or "").strip()
    return candidate.lower() if _COMMIT_SHA.fullmatch(candidate) else None


def latest_cached_revision(repo: str) -> str | None:
    """Return an immutable revision already present in the local HF cache."""
    try:
        from huggingface_hub import scan_cache_dir

        cache = scan_cache_dir()
        matching = next((item for item in cache.repos if item.repo_id == repo), None)
        if matching is None:
            return None
        revisions = sorted(
            matching.revisions,
            key=lambda item: str(getattr(item, "last_modified", "")),
            reverse=True,
        )
        return next(
            (
                revision
                for item in revisions
                if (revision := immutable_revision(getattr(item, "commit_hash", None)))
            ),
            None,
        )
    except Exception:  # noqa: BLE001 - cache metadata is optional and version-dependent
        return None


def resolve_persisted_revision(
    repo: str,
    settings,
    *,
    pinned_repo: str,
    model_info: Callable[[str], object],
    setting_key: str = "model_revision",
    cache_lookup: Callable[[str], object] | None = None,
) -> str | None:
    """Resolve and persist an immutable commit SHA for the configured mirror.

    Moving branch names and malformed persisted values are deliberately not
    accepted as revisions when loading model-provided Python code.
    """

    if repo != pinned_repo:
        return None

    stored = immutable_revision(settings.get(setting_key))
    if stored:
        return stored

    try:
        revision = immutable_revision(getattr(model_info(repo), "sha", None))
    except Exception:  # noqa: BLE001 - third-party network clients raise varied exceptions
        revision = None
    if not revision:
        revision = immutable_revision((cache_lookup or latest_cached_revision)(repo))
    if revision:
        settings.set(setting_key, revision)
    return revision

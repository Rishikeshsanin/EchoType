from __future__ import annotations

import json
import os
import threading
import uuid
from collections.abc import Iterable
from copy import deepcopy
from pathlib import Path
from typing import Any

from echotype.services.settings import VOCABULARY_PATH

DEFAULT_PROFILES = (
    {
        "id": "general",
        "name": "General",
        "terms": (
            ("EchoType", ("echo type",)),
            ("SraVaani", ("sravani", "shravaani", "sra vani", "srivani")),
            ("ARTPARK", ("art park",)),
            ("IISc", ("i i s c", "indian institute of science")),
        ),
    },
    {
        "id": "software-development",
        "name": "Software Development",
        "terms": (
            ("PyTorch", ("pie torch", "py torch")),
            ("Supabase", ("supa base",)),
            ("FastAPI", ("fast a p i", "fast api")),
            ("Kubernetes", ("kuber net ease", "kuberneties")),
            ("GitHub", ("git hub",)),
            ("Vercel", ("versel",)),
            ("NumPy", ("num pie", "numpy")),
            ("SraVaani", ("sravani", "shravaani", "sra vani")),
            ("EchoType", ("echo type",)),
        ),
    },
    {
        "id": "college-academic",
        "name": "College / Academic",
        "terms": (
            ("IISc", ("i i s c", "indian institute of science")),
            ("ARTPARK", ("art park",)),
            ("bibliography", ("bible geography",)),
            ("methodology", ("method ology",)),
        ),
    },
)


def _clean_name(value: Any) -> str:
    name = " ".join(str(value or "").split())
    if not name:
        raise ValueError("Profile name cannot be empty")
    if len(name) > 80:
        raise ValueError("Profile name must be 80 characters or fewer")
    return name


def _clean_term(value: Any) -> str:
    term = " ".join(str(value or "").split())
    if not term:
        raise ValueError("Term cannot be empty")
    if len(term) > 160:
        raise ValueError("Term must be 160 characters or fewer")
    return term


def _clean_aliases(values: Iterable[Any] | str | None, *, term: str = "") -> list[str]:
    source = values.split(",") if isinstance(values, str) else values or []
    aliases: list[str] = []
    seen = {term.casefold()}
    for value in source:
        alias = " ".join(str(value or "").split())
        folded = alias.casefold()
        if not alias or folded in seen:
            continue
        if len(alias) > 160:
            raise ValueError("Aliases must be 160 characters or fewer")
        seen.add(folded)
        aliases.append(alias)
    if len(aliases) > 50:
        raise ValueError("A term can have at most 50 aliases")
    return aliases


def _new_term(term: str, aliases: Iterable[Any] | str | None = None) -> dict[str, Any]:
    canonical = _clean_term(term)
    return {
        "id": uuid.uuid4().hex,
        "term": canonical,
        "aliases": _clean_aliases(aliases, term=canonical),
    }


def _default_data() -> dict[str, Any]:
    profiles = []
    for profile in DEFAULT_PROFILES:
        profiles.append(
            {
                "id": profile["id"],
                "name": profile["name"],
                "terms": [_new_term(term, aliases) for term, aliases in profile["terms"]],
            }
        )
    return {"version": 1, "active_profile_id": "general", "profiles": profiles}


class VocabularyService:
    """Persisted terminology profiles used directly by transcript cleanup."""

    def __init__(
        self,
        path: Path = VOCABULARY_PATH,
        *,
        legacy_terms: Iterable[Any] | None = None,
    ) -> None:
        self.path = path
        self._lock = threading.RLock()
        self._data = _default_data()
        existed = self.path.exists()
        self.load()
        if not existed and legacy_terms:
            self._import_legacy(legacy_terms)
            self.save()

    def _import_legacy(self, terms: Iterable[Any]) -> None:
        """Move the old flat settings vocabulary into the General profile."""
        general = self._find_profile("general")
        existing = {entry["term"].casefold() for entry in general["terms"]}
        for item in terms:
            if isinstance(item, dict):
                term = item.get("term")
                aliases = item.get("aliases")
            else:
                term = item
                aliases = None
            try:
                entry = _new_term(str(term or ""), aliases)
            except ValueError:
                continue
            if entry["term"].casefold() not in existing:
                general["terms"].append(entry)
                existing.add(entry["term"].casefold())

    def load(self) -> None:
        try:
            if not self.path.exists():
                return
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            normalized = self._normalize_data(raw)
        except (OSError, TypeError, ValueError):
            return
        with self._lock:
            self._data = normalized

    @staticmethod
    def _normalize_data(raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict) or not isinstance(raw.get("profiles"), list):
            raise TypeError("Invalid vocabulary file")
        profiles: list[dict[str, Any]] = []
        profile_ids: set[str] = set()
        profile_names: set[str] = set()
        for item in raw["profiles"]:
            if not isinstance(item, dict):
                continue
            name = _clean_name(item.get("name"))
            profile_id = str(item.get("id") or uuid.uuid4().hex).strip()
            if not profile_id or profile_id in profile_ids or name.casefold() in profile_names:
                continue
            terms: list[dict[str, Any]] = []
            term_names: set[str] = set()
            for candidate in item.get("terms", []):
                if not isinstance(candidate, dict):
                    continue
                try:
                    term = _clean_term(candidate.get("term"))
                    if term.casefold() in term_names:
                        continue
                    terms.append(
                        {
                            "id": str(candidate.get("id") or uuid.uuid4().hex),
                            "term": term,
                            "aliases": _clean_aliases(candidate.get("aliases"), term=term),
                        }
                    )
                    term_names.add(term.casefold())
                except ValueError:
                    continue
            profiles.append({"id": profile_id, "name": name, "terms": terms})
            profile_ids.add(profile_id)
            profile_names.add(name.casefold())
        if not profiles:
            raise ValueError("Vocabulary must contain at least one profile")
        active = str(raw.get("active_profile_id") or "")
        if active not in profile_ids:
            active = profiles[0]["id"]
        return {"version": 1, "active_profile_id": active, "profiles": profiles}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with self._lock:
            payload = json.dumps(self._data, indent=2, ensure_ascii=False)
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, self.path)

    def profiles(self) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(self._data["profiles"])

    @property
    def active_profile_id(self) -> str:
        with self._lock:
            return str(self._data["active_profile_id"])

    def get_profile(self, profile_id: str) -> dict[str, Any]:
        with self._lock:
            profile = self._find_profile(profile_id)
            return deepcopy(profile)

    def _find_profile(self, profile_id: str) -> dict[str, Any]:
        for profile in self._data["profiles"]:
            if profile["id"] == profile_id:
                return profile
        raise KeyError(f"Unknown vocabulary profile: {profile_id}")

    def _ensure_unique_profile_name(self, name: str, *, excluding: str | None = None) -> None:
        for profile in self._data["profiles"]:
            if profile["id"] != excluding and profile["name"].casefold() == name.casefold():
                raise ValueError("A profile with that name already exists")

    def create_profile(self, name: str) -> dict[str, Any]:
        normalized = _clean_name(name)
        with self._lock:
            self._ensure_unique_profile_name(normalized)
            profile = {"id": uuid.uuid4().hex, "name": normalized, "terms": []}
            self._data["profiles"].append(profile)
            self.save()
            return deepcopy(profile)

    def rename_profile(self, profile_id: str, name: str) -> dict[str, Any]:
        normalized = _clean_name(name)
        with self._lock:
            self._ensure_unique_profile_name(normalized, excluding=profile_id)
            profile = self._find_profile(profile_id)
            profile["name"] = normalized
            self.save()
            return deepcopy(profile)

    def delete_profile(self, profile_id: str) -> None:
        with self._lock:
            if len(self._data["profiles"]) <= 1:
                raise ValueError("At least one vocabulary profile is required")
            self._find_profile(profile_id)
            self._data["profiles"] = [
                profile for profile in self._data["profiles"] if profile["id"] != profile_id
            ]
            if self._data["active_profile_id"] == profile_id:
                self._data["active_profile_id"] = self._data["profiles"][0]["id"]
            self.save()

    def activate_profile(self, profile_id: str) -> None:
        with self._lock:
            self._find_profile(profile_id)
            self._data["active_profile_id"] = profile_id
            self.save()

    @staticmethod
    def _ensure_unique_term(
        profile: dict[str, Any], term: str, excluding: str | None = None
    ) -> None:
        for item in profile["terms"]:
            if item["id"] != excluding and item["term"].casefold() == term.casefold():
                raise ValueError("That term already exists in this profile")

    def add_term(
        self,
        profile_id: str,
        term: str,
        aliases: Iterable[Any] | str | None = None,
    ) -> dict[str, Any]:
        entry = _new_term(term, aliases)
        with self._lock:
            profile = self._find_profile(profile_id)
            self._ensure_unique_term(profile, entry["term"])
            profile["terms"].append(entry)
            self.save()
            return deepcopy(entry)

    def edit_term(
        self,
        profile_id: str,
        term_id: str,
        term: str,
        aliases: Iterable[Any] | str | None = None,
    ) -> dict[str, Any]:
        canonical = _clean_term(term)
        cleaned_aliases = _clean_aliases(aliases, term=canonical)
        with self._lock:
            profile = self._find_profile(profile_id)
            self._ensure_unique_term(profile, canonical, excluding=term_id)
            for entry in profile["terms"]:
                if entry["id"] == term_id:
                    entry.update(term=canonical, aliases=cleaned_aliases)
                    self.save()
                    return deepcopy(entry)
        raise KeyError(f"Unknown vocabulary term: {term_id}")

    def delete_term(self, profile_id: str, term_id: str) -> None:
        with self._lock:
            profile = self._find_profile(profile_id)
            before = len(profile["terms"])
            profile["terms"] = [entry for entry in profile["terms"] if entry["id"] != term_id]
            if len(profile["terms"]) == before:
                raise KeyError(f"Unknown vocabulary term: {term_id}")
            self.save()

    def search(self, query: str, profile_id: str | None = None) -> list[dict[str, Any]]:
        needle = str(query or "").strip().casefold()
        profile = self.get_profile(profile_id or self.active_profile_id)
        if not needle:
            return profile["terms"]
        return [
            term
            for term in profile["terms"]
            if needle in term["term"].casefold()
            or any(needle in alias.casefold() for alias in term["aliases"])
        ]

    def active_terms(self) -> list[dict[str, Any]]:
        with self._lock:
            profile = self._find_profile(self._data["active_profile_id"])
            return deepcopy(profile["terms"])

    def apply(self, text: str) -> str:
        # Kept here as a convenient service-level API while the deterministic
        # replacement implementation remains in the cleanup module.
        from echotype.core.cleanup import apply_vocabulary

        return apply_vocabulary(text, self.active_terms())

from __future__ import annotations

import collections
import unicodedata

SHORT_UTTERANCE_SECONDS = 4.0
MIN_TOKENS_FOR_TRUST = 3


def dominant_script(text: str) -> str | None:
    counts: collections.Counter[str] = collections.Counter()
    for char in text or "":
        if not char.isalpha():
            continue
        try:
            counts[unicodedata.name(char).split(" ")[0]] += 1
        except ValueError:
            continue
    return counts.most_common(1)[0][0] if counts else None


class LanguageTracker:
    """Sticky session-script prior for acoustically ambiguous short utterances."""

    def __init__(self, switch_evidence: int = 2) -> None:
        if switch_evidence < 1:
            raise ValueError("switch_evidence must be at least one")
        self.switch_evidence = switch_evidence
        self._session: str | None = None
        self._pending: str | None = None
        self._pending_hits = 0

    def reset(self) -> None:
        self._session = None
        self._pending = None
        self._pending_hits = 0

    @property
    def session_script(self) -> str | None:
        return self._session

    def prior_for(self, seconds: float) -> str | None:
        return None if seconds >= SHORT_UTTERANCE_SECONDS else self._session

    def observe(self, script: str | None, seconds: float, tokens: int) -> str | None:
        del seconds
        if not script or tokens < MIN_TOKENS_FOR_TRUST:
            return self._session
        if self._session is None:
            self._session = script
            self._pending = None
            self._pending_hits = 0
            return script
        if script == self._session:
            self._pending = None
            self._pending_hits = 0
            return script

        if self._pending == script:
            self._pending_hits += 1
        else:
            self._pending = script
            self._pending_hits = 1

        if self._pending_hits >= self.switch_evidence:
            self._session = script
            self._pending = None
            self._pending_hits = 0
            return script
        return self._session

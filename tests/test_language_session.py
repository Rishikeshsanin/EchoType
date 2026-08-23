from __future__ import annotations

import pytest

from echotype.core.language_session import LanguageTracker, dominant_script
from echotype.core.languages import AUTO, code_for_name, describe, script_for_code


@pytest.mark.parametrize(
    ("text", "script"),
    [
        ("hello", "LATIN"),
        ("नमस्ते", "DEVANAGARI"),
        ("ನಮಸ್ಕಾರ", "KANNADA"),
        ("வணக்கம்", "TAMIL"),
        ("నమస్కారం", "TELUGU"),
    ],
)
def test_dominant_script_for_release_languages(text: str, script: str) -> None:
    assert dominant_script(text) == script


def test_auto_metadata_labels_shared_script_as_hint_not_language_id() -> None:
    metadata = describe("नमस्ते", AUTO)
    assert metadata["script"] == "DEVANAGARI"
    assert metadata["language"] == "Hindi"
    assert metadata["is_script_hint"] is True
    assert "Script hint only" in str(metadata["note"])


def test_manual_language_metadata_reports_script_mismatch() -> None:
    metadata = describe("hello", "te")
    assert metadata["language"] == "Telugu"
    assert metadata["script"] == "LATIN"
    assert metadata["mismatch"] is True


@pytest.mark.parametrize("name", ["English", "Telugu", "Hindi", "Kannada", "Tamil"])
def test_required_manual_languages_have_script_locks(name: str) -> None:
    code = code_for_name(name)
    assert code != AUTO
    assert script_for_code(code)


def test_short_utterance_inherits_established_session_script() -> None:
    tracker = LanguageTracker()
    assert tracker.observe("LATIN", seconds=5.0, tokens=8) == "LATIN"
    assert tracker.prior_for(1.0) == "LATIN"
    assert tracker.prior_for(4.0) is None


def test_tracker_requires_two_conflicting_observations_before_switch() -> None:
    tracker = LanguageTracker(switch_evidence=2)
    tracker.observe("LATIN", seconds=5.0, tokens=8)
    assert tracker.observe("DEVANAGARI", seconds=5.0, tokens=8) == "LATIN"
    assert tracker.session_script == "LATIN"
    assert tracker.observe("DEVANAGARI", seconds=5.0, tokens=8) == "DEVANAGARI"
    assert tracker.session_script == "DEVANAGARI"


def test_tracker_ignores_too_little_token_evidence_and_resets() -> None:
    tracker = LanguageTracker()
    assert tracker.observe("LATIN", seconds=5.0, tokens=2) is None
    tracker.observe("LATIN", seconds=5.0, tokens=3)
    tracker.reset()
    assert tracker.session_script is None
    assert tracker.prior_for(1.0) is None

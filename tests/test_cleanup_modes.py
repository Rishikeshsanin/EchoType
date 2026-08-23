from __future__ import annotations

from types import SimpleNamespace

import pytest

from echotype.core.cleanup import SMART, VERBATIM, clean, clean_hypothesis


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("um actually keep these words", "um actually keep these words"),
        ("dont merge every one", "dont merge every one"),
        ("say comma then full stop", "say comma then full stop"),
        ("తెలుగు పదాలు అలాగే ఉంచు", "తెలుగు పదాలు అలాగే ఉంచు"),
    ],
)
def test_verbatim_preserves_literal_words_and_punctuation(source: str, expected: str) -> None:
    result = clean(source, mode=VERBATIM, vocabulary=["EchoType"])
    assert result.text == expected
    assert result.changed is False


def test_verbatim_only_normalizes_decoder_whitespace() -> None:
    result = clean("  one\t two \n three  ", mode=VERBATIM)
    assert result.text == "one two\nthree"
    assert result.changed is True


def test_verbatim_ignores_timestamp_punctuation_and_vocabulary() -> None:
    hypothesis = SimpleNamespace(
        text="echo type comma keep um",
        timestamp={
            "word": [
                {"word": "echo", "start": 0.0, "end": 1.0},
                {"word": "type", "start": 2.0, "end": 2.2},
            ]
        },
    )
    result = clean_hypothesis(hypothesis, mode=VERBATIM, vocabulary=["EchoType"])
    assert result.text == "echo type comma keep um"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "um i dont think this works comma actually it does full stop",
            "I don't think this works, actually it does.",
        ),
        ("wait wait wait this is fine", "Wait this is fine"),
        ("thankyou every one", "Thank you everyone"),
    ],
)
def test_smart_mode_applies_documented_deterministic_transformations(
    source: str, expected: str
) -> None:
    assert clean(source, mode=SMART).text == expected


def test_smart_filler_matching_does_not_change_substrings() -> None:
    result = clean("i said umami thermal and erlang", mode=SMART)
    assert result.text == "I said umami thermal and erlang"


def test_unknown_mode_falls_back_to_smart_and_reports_effective_mode() -> None:
    result = clean("hello comma world", mode="not-a-mode")
    assert result.mode == SMART
    assert result.text == "Hello, world"

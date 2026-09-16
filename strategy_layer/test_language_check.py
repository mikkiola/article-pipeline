"""Tests for strategy_layer/language_check.py — the optional runtime
safety-net heuristic for Habr-bound framing text (SPEC.md's Gap 1 fix:
the primary mechanism is instructing the automated framing producer to
write Russian for Habr-bound content; this is the explicitly-optional
backstop the owner invited, "policing arbitrary text after the fact"
only as a cheap secondary check, not the primary fix).

Deliberately a crude heuristic, not a language-detection library
dependency — a ratio-of-Cyrillic-characters check catches the obvious
failure mode (framing producer forgot the Russian instruction, text
came out entirely in English) without claiming to validate actual
grammatical correctness or native fluency, which is out of a static
check's reach.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import language_check  # noqa: E402


def test_pure_russian_text_passes():
    text = "Активность в этом репозитории выросла на этой неделе."
    assert language_check.looks_russian(text) is True


def test_pure_english_text_fails():
    text = "Activity in this repository increased this week."
    assert language_check.looks_russian(text) is False


def test_empty_string_fails():
    assert language_check.looks_russian("") is False


def test_mixed_text_with_majority_cyrillic_passes():
    # A code identifier or repo name in Latin script alongside Russian
    # prose shouldn't fail the check — only a genuinely non-Russian body.
    text = "В репозитории article-pipeline было 6 коммитов на этой неделе."
    assert language_check.looks_russian(text) is True


def test_mixed_text_with_majority_latin_fails():
    text = "Repository article-pipeline had шесть commits this week overall."
    assert language_check.looks_russian(text) is False


def test_default_threshold_is_configurable():
    text = "Половина русский half english текст."
    # Right at/near the boundary — exercise the threshold parameter
    # directly rather than relying on the default's exact behavior.
    assert language_check.looks_russian(text, min_cyrillic_ratio=0.9) is False
    assert language_check.looks_russian(text, min_cyrillic_ratio=0.1) is True

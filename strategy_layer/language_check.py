"""Optional runtime safety-net heuristic for Habr-bound framing text
(SPEC.md's Gap 1 fix — the primary mechanism is instructing the
automated framing producer to write Russian for Habr-bound content;
this is the explicitly-optional backstop, not the primary fix).

Deliberately crude: a ratio-of-Cyrillic-letters check, not a language-
detection library dependency. Catches the obvious failure mode (the
framing producer forgot the Russian instruction, text came out
entirely or mostly in English) without claiming to validate actual
grammatical correctness or native fluency — out of a static check's
reach, and not what this is for.
"""

from __future__ import annotations

_CYRILLIC_RANGE = (0x0400, 0x04FF)


def _is_cyrillic_letter(ch: str) -> bool:
    return _CYRILLIC_RANGE[0] <= ord(ch) <= _CYRILLIC_RANGE[1]


def looks_russian(text: str, min_cyrillic_ratio: float = 0.5) -> bool:
    """Returns True iff the ratio of Cyrillic letters among all alphabetic
    characters in `text` meets or exceeds `min_cyrillic_ratio`.

    Non-alphabetic characters (digits, punctuation, whitespace, hyphens
    in identifiers like "article-pipeline") are excluded from both the
    numerator and denominator — a Latin-script repo name or code
    identifier embedded in otherwise-Russian prose shouldn't by itself
    fail the check. Empty text, or text with no alphabetic characters
    at all, returns False (nothing to confirm as Russian).
    """
    alpha_chars = [ch for ch in text if ch.isalpha()]
    if not alpha_chars:
        return False

    cyrillic_count = sum(1 for ch in alpha_chars if _is_cyrillic_letter(ch))
    ratio = cyrillic_count / len(alpha_chars)
    return ratio >= min_cyrillic_ratio

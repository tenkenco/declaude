"""Guard the model's output at the boundary.

Small open-weight models occasionally leak their own commentary or answer in the wrong
language. Both are worse than doing nothing, so the rewrite is rejected in favour of the
original text when it fails these checks.
"""
import re
import unicodedata

_META_MARKERS = (
    "翻译：", "翻译:", "根据指示", "说明：",
    "Translation:", "Note:", "Explanation:", "Rewritten text:",
)
_PREAMBLE = re.compile(
    r"^\s*(sure|certainly|here(?:'s| is)|okay|ok)[^\n:]{0,60}:\s*\n+", re.IGNORECASE
)

_RANGES = (
    ("hiragana", 0x3040, 0x309F), ("katakana", 0x30A0, 0x30FF),
    ("han", 0x4E00, 0x9FFF), ("hangul", 0xAC00, 0xD7AF),
    ("arabic", 0x0600, 0x06FF), ("hebrew", 0x0590, 0x05FF),
    ("cyrillic", 0x0400, 0x04FF), ("devanagari", 0x0900, 0x097F),
    ("greek", 0x0370, 0x03FF), ("thai", 0x0E00, 0x0E7F),
)


def _script_of(ch: str) -> str | None:
    if not ch.isalpha():
        return None
    cp = ord(ch)
    for name, lo, hi in _RANGES:
        if lo <= cp <= hi:
            return name
    return "latin" if "LATIN" in unicodedata.name(ch, "") else None


def dominant_script(text: str) -> str:
    counts: dict[str, int] = {}
    for ch in text:
        s = _script_of(ch)
        if s:
            counts[s] = counts.get(s, 0) + 1
    if not counts:
        return "none"
    # kana anywhere means Japanese, even when han characters outnumber it
    if counts.get("hiragana", 0) + counts.get("katakana", 0) > 0:
        return "japanese"
    return max(counts, key=lambda k: counts[k])


def clean_output(original: str, translated: str) -> str:
    """Return a safe rewrite, or the original when the model misbehaved."""
    text = (translated or "").strip()
    for marker in _META_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx].strip()
    text = _PREAMBLE.sub("", text).strip()
    if not text:
        return original
    if dominant_script(text) != dominant_script(original):
        return original
    return text

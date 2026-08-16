"""Guard against silent fact loss in a rewrite.

The 14B model occasionally deletes a whole paragraph rather than rewriting it. Paragraphs that
mention prompts, credits, or sources are the most frequent casualties — found by dogfooding, where
a line crediting `gvzdv/claudish-to-english` was dropped on every run of a long post.

Strategy: extract the tokens a style rewrite has no business changing (URLs, emails, handles,
`owner/repo` slugs, license identifiers), check they survived, and re-translate only the paragraphs
that lost one. Put each repaired paragraph back where it came from — replacing the model's version
if it produced one, inserting it if the paragraph vanished outright. If the model drops the token a
second time, keep the author's original sentence.
"""
import difflib
import re

_PATTERNS = (
    r"https?://[^\s<>\)\]]+",                     # URLs
    r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",              # emails
    r"(?<![\w/])@[A-Za-z0-9_-]{2,}\b",             # @handles
    r"(?<![\w/@$])[A-Za-z][A-Za-z0-9_.-]+/[A-Za-z0-9_.-]*[A-Za-z][A-Za-z0-9_.-]*(?![\w/])",  # owner/repo
    r"\b(?:Apache|GPL|LGPL|AGPL|MPL|BSD|CC|EPL)-[\d.]+(?:-[A-Za-z]+)?\b",  # SPDX-ish licenses
)
_TOKEN = re.compile("|".join(f"(?:{p})" for p in _PATTERNS))

# Slug-shaped things that are ordinary prose or units, not identifiers.
_NOT_A_SLUG = re.compile(r"^(?:and/or|his/her|he/she|w/o|km/h|m/s|kg/m|n/a|input/output)$", re.IGNORECASE)

# A paragraph pair this similar is the same paragraph, reworded.
_SAME_PARAGRAPH = 0.45


def salient_tokens(text: str) -> list[str]:
    """Tokens a style rewrite must preserve verbatim, in order of appearance, deduplicated."""
    seen: dict[str, None] = {}
    for match in _TOKEN.finditer(text):
        token = match.group(0).rstrip(".,;:!?")
        if not token.startswith(("http", "@")) and "/" in token and _NOT_A_SLUG.match(token):
            continue
        seen.setdefault(token, None)
    return list(seen)


def missing_tokens(source: str, output: str) -> list[str]:
    """Salient tokens present in the source that did not survive into the output."""
    return [t for t in salient_tokens(source) if t not in output]


def paragraphs(text: str) -> list[str]:
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


def _counterpart(para: str, candidates: list[str], taken: set[int]) -> int | None:
    """Index of the output paragraph that is this source paragraph, reworded — if any."""
    best, best_ratio = None, _SAME_PARAGRAPH
    for i, candidate in enumerate(candidates):
        if i in taken:
            continue
        ratio = difflib.SequenceMatcher(None, para, candidate).ratio()
        if ratio > best_ratio:
            best, best_ratio = i, ratio
    return best


async def repair(source: str, output: str, retranslate) -> str:
    """Restore facts the rewrite lost. `retranslate` is an async str -> str.

    Costs nothing when the model behaved: no missing tokens means no extra call.
    """
    if not missing_tokens(source, output):
        return output

    src_paras = paragraphs(source)
    out_paras = paragraphs(output)
    taken: set[int] = set()
    slots: list[int | None] = []
    for para in src_paras:
        slot = _counterpart(para, out_paras, taken)
        if slot is not None:
            taken.add(slot)
        slots.append(slot)

    for index, para in enumerate(src_paras):
        needed = [t for t in salient_tokens(para) if t not in output]
        if not needed:
            continue
        try:
            fixed = (await retranslate(para)).strip()
        except Exception:  # noqa: BLE001 - a failed repair must never fail the whole request
            fixed = ""
        if not fixed or any(t not in fixed for t in needed):
            fixed = para.strip()  # the model is incorrigible here; ship the author's words

        slot = slots[index]
        if slot is None:  # the paragraph vanished; put it back after its predecessor
            before = [s for s in slots[:index] if s is not None]
            slot = (before[-1] + 1) if before else 0
            out_paras.insert(min(slot, len(out_paras)), fixed)
            slots = [s + 1 if s is not None and s >= slot else s for s in slots]
            slots[index] = slot
        else:
            out_paras[slot] = fixed
        output = "\n\n".join(out_paras)
    return output

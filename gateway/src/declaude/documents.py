"""Document translation: split into blocks, de-Claude the prose, keep code verbatim.

The domain model is the Block: a document is a sequence of prose and code blocks.
Code fences, indented code, and headings-only blocks pass through untouched;
prose blocks go through the model one call per block, concurrently.
"""
import asyncio
import re
from dataclasses import dataclass

from .model import ModelClient
from .prompts import SYSTEM_PROMPT


class ModelUnavailable(RuntimeError):
    """Raised when no block could be translated at all — the caller should return 503."""


CHUNK_CHARS = 2500
MAX_BLOCK_CHARS = 2500  # a single prose block larger than this is subdivided before the model
ALLOWED_SUFFIXES = {".md", ".markdown", ".txt", ".rst"}


@dataclass(frozen=True)
class Block:
    kind: str  # "prose" | "code"
    text: str


def _subdivide(text: str, limit: int = MAX_BLOCK_CHARS) -> list[str]:
    """Break an oversized prose block on sentence boundaries, then hard-wrap as a last resort."""
    if len(text) <= limit:
        return [text]
    pieces: list[str] = []
    buf = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        while len(sentence) > limit:  # a single monstrous sentence
            pieces.append(sentence[:limit])
            sentence = sentence[limit:]
        if len(buf) + len(sentence) + 1 > limit and buf:
            pieces.append(buf.strip())
            buf = ""
        buf += (" " if buf else "") + sentence
    if buf.strip():
        pieces.append(buf.strip())
    return pieces


def split_blocks(text: str) -> list[Block]:
    """Split on blank lines; fenced blocks (``` or ~~~) stay single code blocks."""
    blocks: list[Block] = []
    lines = text.strip().split("\n")
    i = 0
    para: list[str] = []

    def flush():
        if para:
            joined = "\n".join(para)
            for piece in _subdivide(joined):
                blocks.append(Block("prose", piece))
            para.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            flush()
            fence = stripped[:3]
            code = [line]
            i += 1
            while i < len(lines):
                code.append(lines[i])
                if lines[i].lstrip().startswith(fence):
                    break
                i += 1
            blocks.append(Block("code", "\n".join(code)))
        elif not line.strip():
            flush()
        else:
            para.append(line)
        i += 1
    flush()
    return blocks


def _translatable(block: Block) -> bool:
    if block.kind == "code":
        return False
    t = block.text.strip()
    # headings, tables, and link-reference lines carry structure, not Claude-voice
    return not (t.startswith("#") and "\n" not in t) and not t.startswith("|")


async def translate_document(text: str, model: ModelClient, concurrency: int = 6) -> str:
    """Translate every prose block independently, in parallel, preserving structure 1:1.

    One model call per block is the only scheme where a block cannot vanish: no count
    matching, no merging. Bounded concurrency keeps it faster than the sequential batching
    it replaces, since vLLM batches concurrent requests. A block whose call fails keeps its
    original text — degraded, never dropped.
    """
    blocks = split_blocks(text)
    out = [b.text for b in blocks]
    sem = asyncio.Semaphore(concurrency)
    targets = [i for i, b in enumerate(blocks) if _translatable(b)]
    failures = 0

    async def render(idx: int, block: Block) -> None:
        nonlocal failures
        async with sem:
            try:
                result = (await model.complete(SYSTEM_PROMPT, block.text)).strip()
            except Exception:  # noqa: BLE001 - any upstream failure degrades this block only
                failures += 1  # keep the original text for this block
                return
            if result:
                out[idx] = result

    await asyncio.gather(*(render(i, blocks[i]) for i in targets))
    if targets and failures == len(targets):
        raise ModelUnavailable("every block failed to translate")
    return "\n\n".join(out) + "\n"

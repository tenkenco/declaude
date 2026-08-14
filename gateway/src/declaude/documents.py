"""Document translation: split into blocks, de-Claude the prose, keep code verbatim.

The domain model is the Block: a document is a sequence of prose and code blocks.
Code fences, indented code, and headings-only blocks pass through untouched;
prose blocks go through the model in batched chunks.
"""
from dataclasses import dataclass

from .model import ModelClient
from .prompts import SYSTEM_PROMPT

CHUNK_CHARS = 2500
ALLOWED_SUFFIXES = {".md", ".markdown", ".txt", ".rst"}


@dataclass(frozen=True)
class Block:
    kind: str  # "prose" | "code"
    text: str


def split_blocks(text: str) -> list[Block]:
    """Split on blank lines; fenced blocks (``` or ~~~) stay single code blocks."""
    blocks: list[Block] = []
    lines = text.strip().split("\n")
    i = 0
    para: list[str] = []

    def flush():
        if para:
            blocks.append(Block("prose", "\n".join(para)))
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


async def translate_document(text: str, model: ModelClient) -> str:
    blocks = split_blocks(text)
    out: list[str] = [b.text for b in blocks]
    # batch consecutive translatable blocks into chunks to cut round-trips
    batch: list[int] = []
    size = 0

    async def flush_batch():
        nonlocal size
        if not batch:
            return
        joined = "\n\n".join(out[j] for j in batch)
        translated = await model.complete(SYSTEM_PROMPT, joined)
        parts = translated.split("\n\n")
        if len(parts) == len(batch):
            for j, part in zip(batch, parts):
                out[j] = part.strip()
        else:  # model merged/split paragraphs; keep its prose as one block
            out[batch[0]] = translated.strip()
            for j in batch[1:]:
                out[j] = ""
        batch.clear()
        size = 0

    for idx, b in enumerate(blocks):
        if _translatable(b):
            if size + len(b.text) > CHUNK_CHARS:
                await flush_batch()
            batch.append(idx)
            size += len(b.text)
        else:
            await flush_batch()
    await flush_batch()
    return "\n\n".join(s for s in out if s) + "\n"

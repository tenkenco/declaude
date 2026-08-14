"""Document upload: de-Claude a whole file, gated by doc-count and file-size quotas."""
import pytest
from conftest import FakeAuth
from fastapi.testclient import TestClient

from declaude.app import create_app
from declaude.config import Settings
from declaude.documents import split_blocks

BH = {"Authorization": "Bearer valid-token"}
MD = """# Title

Great question! This is a robust solution.

```python
def f():  # code must survive verbatim
    return 1
```

Absolutely right — comprehensive and production-ready.
"""


@pytest.fixture
def client(model, usage):
    s = Settings(
        free_tier_monthly_documents=2,
        doc_max_bytes_free=1000,
        doc_max_bytes_paid=5000,
        stripe_payment_link="https://buy.stripe.com/x",
    )
    return TestClient(create_app(model=model, auth=FakeAuth(), usage=usage, settings=s))


MD_BYTES = MD.encode()


def up(client, name="doc.md", content=MD_BYTES):
    return client.post("/v1/documents", files={"file": (name, content, "text/markdown")}, headers=BH)


# --- splitting (pure domain logic) ---

def test_split_preserves_code_fences():
    blocks = split_blocks(MD)
    kinds = [b.kind for b in blocks]
    assert "code" in kinds and "prose" in kinds
    code = next(b for b in blocks if b.kind == "code")
    assert "def f():" in code.text


def test_split_roundtrips_verbatim():
    assert "\n\n".join(b.text for b in split_blocks(MD)) == MD.strip()


# --- endpoint ---

def test_requires_auth(client):
    r = client.post("/v1/documents", files={"file": ("a.md", b"hi", "text/markdown")})
    assert r.status_code == 401


def test_translates_prose_keeps_code(client):
    r = up(client)
    assert r.status_code == 200
    body = r.text
    assert "PLAIN::" in body                      # prose went through the model
    assert "def f():  # code must survive verbatim" in body   # code untouched
    assert "# Title" in body                      # heading preserved
    assert r.headers["content-disposition"].startswith("attachment")
    assert "doc.declauded.md" in r.headers["content-disposition"]


def test_doc_quota_402_with_upgrade(client):
    assert up(client).status_code == 200
    assert up(client).status_code == 200
    r = up(client)
    assert r.status_code == 402
    assert "upgrade_url" in r.text


def test_size_limit_free_413(client):
    r = up(client, content=b"word " * 300)  # >1000 bytes
    assert r.status_code == 413


def test_paid_gets_bigger_files_and_more_docs(client, usage):
    import anyio
    anyio.run(usage.set_paid, "user_123", True)
    assert up(client, content=b"Claude prose here. " * 100).status_code == 200  # ~1.9KB ok for paid
    for _ in range(3):
        assert up(client).status_code == 200  # beyond free doc count


def test_unsupported_type_415(client):
    r = up(client, name="a.pdf", content=b"%PDF-1.4")
    assert r.status_code == 415


def test_upload_page_served(client):
    r = client.get("/documents")
    assert r.status_code == 200
    assert "upload" in r.text.lower()


def test_filename_cannot_inject_headers(client):
    r = up(client, name='a".md\r\nX-Evil: 1')
    assert r.status_code in (200, 415)
    if r.status_code == 200:
        assert "X-Evil" not in r.headers
        assert "\r" not in r.headers.get("content-disposition", "")

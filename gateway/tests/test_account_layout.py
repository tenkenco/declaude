"""Account page structure: do the thing first, configure second, never lose the key."""
import pytest
from conftest import FakeAuth
from fastapi.testclient import TestClient

from declaude.app import create_app
from declaude.config import Settings


@pytest.fixture
def client(model, usage):
    s = Settings(clerk_publishable_key="pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk")
    return TestClient(create_app(model=model, auth=FakeAuth(), usage=usage, settings=s))


def test_documents_section_comes_before_keys(client):
    html = client.get("/signin").text
    assert html.index('id="docs-card"') < html.index('id="keys-card"')


def test_new_key_is_shown_in_a_modal(client):
    html = client.get("/signin").text
    assert "<dialog" in html and 'id="key-modal"' in html
    assert "showModal()" in html


def test_no_legacy_label(client):
    assert "legacy" not in client.get("/signin").text.lower()


def test_keys_section_explains_purpose(client):
    html = client.get("/signin").text
    assert "hook" in html.lower() and "mcp" in html.lower()

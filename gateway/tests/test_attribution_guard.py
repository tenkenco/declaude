"""Regression: the rewriter must not silently drop attribution.

Found by dogfooding the launch post through the live service: a paragraph crediting
`gvzdv/claudish-to-english` was deleted on every run, while the rest of the text survived.
A style rewriter that eats an open-source credit is worse than one that does nothing.
"""
import pytest
from conftest import AUTH

from declaude.guard import missing_tokens, salient_tokens

CREDIT = "The rewriting prompt is adapted from gvzdv/claudish-to-english, the original local-Ollama hook."
POST = (
    "Great question! I am thrilled to share our comprehensive new service.\n\n"
    "It is worth noting that it delivers robust performance.\n\n"
    + CREDIT
)


class DroppingModel:
    """Stands in for the real 14B model, which deletes paragraphs that mention prompts."""

    def __init__(self, drops: str, times: int = 99):
        self.drops, self.times, self.calls = drops, times, []

    async def complete(self, system: str, prompt: str) -> str:
        self.calls.append(prompt)
        kept = [p for p in prompt.split("\n\n") if self.drops not in p or len(self.calls) > self.times]
        return "\n\n".join(f"PLAIN::{p}" for p in kept)


def test_salient_tokens_finds_credits_urls_and_handles():
    text = "See https://example.com/a?b=1 or email ops@example.com about gvzdv/claudish-to-english (@someone)."
    found = salient_tokens(text)
    assert "https://example.com/a?b=1" in found
    assert "ops@example.com" in found
    assert "gvzdv/claudish-to-english" in found
    assert "@someone" in found


def test_salient_tokens_ignores_ordinary_prose():
    assert salient_tokens("This is a plain sentence about writing and style.") == []


def test_missing_tokens_reports_only_what_vanished():
    src = "Credit: gvzdv/claudish-to-english and https://example.com/x"
    assert missing_tokens(src, "Credit: gvzdv/claudish-to-english") == ["https://example.com/x"]
    assert missing_tokens(src, src) == []


def test_translate_restores_a_dropped_attribution(client_with, model_drops):
    """The endpoint must return the credit even though the model deletes it on the first pass."""
    r = client_with.post("/v1/translate", json={"text": POST}, headers=AUTH)
    assert r.status_code == 200
    assert "gvzdv/claudish-to-english" in r.json()["translation"]


def test_repair_retranslates_only_the_lost_paragraph(client_with, model_drops):
    client_with.post("/v1/translate", json={"text": POST}, headers=AUTH)
    assert len(model_drops.calls) == 2, "one full pass, then one repair pass"
    assert model_drops.calls[1].strip() == CREDIT, "repair pass sends only the lost paragraph"


def test_repair_keeps_paragraph_order(client_with, model_drops):
    out = client_with.post("/v1/translate", json={"text": POST}, headers=AUTH).json()["translation"]
    paras = [p for p in out.split("\n\n") if p.strip()]
    assert len(paras) == 3
    assert "gvzdv/claudish-to-english" in paras[-1], "credit stays last, where the author put it"


def test_incorrigible_model_falls_back_to_the_original_text(client_with_always_dropping):
    """If the repair pass drops it too, ship the author's own sentence rather than lose it."""
    out = client_with_always_dropping.post("/v1/translate", json={"text": POST}, headers=AUTH).json()["translation"]
    assert CREDIT in out, "verbatim fallback"


def test_happy_path_costs_no_extra_model_call(client, model):
    client.post("/v1/translate", json={"text": "Great question! Thanks."}, headers=AUTH)
    assert len(model.calls) == 1, "the guard must be free when nothing is dropped"


@pytest.fixture
def model_drops():
    return DroppingModel("gvzdv", times=1)


@pytest.fixture
def client_with(model_drops, usage, settings):
    from conftest import FakeAuth
    from fastapi.testclient import TestClient

    from declaude.app import create_app

    return TestClient(create_app(model=model_drops, auth=FakeAuth(), usage=usage, settings=settings))


@pytest.fixture
def client_with_always_dropping(usage, settings):
    from conftest import FakeAuth
    from fastapi.testclient import TestClient

    from declaude.app import create_app

    return TestClient(
        create_app(model=DroppingModel("gvzdv", times=99), auth=FakeAuth(), usage=usage, settings=settings)
    )


def test_price_and_unit_slugs_are_not_identifiers():
    """`$5/month` and `24/7` look like owner/repo slugs but are prose. Found live: a false
    positive here made the repair pass duplicate a whole paragraph."""
    assert salient_tokens("It costs $5/month, support is 24/7, and speed is 30 km/h.") == []
    assert salient_tokens("Credit: gvzdv/claudish-to-english") == ["gvzdv/claudish-to-english"]


class RewordingModel:
    """Keeps every paragraph but rewrites a URL away — the guard must replace, not duplicate."""

    def __init__(self):
        self.calls: list[str] = []

    async def complete(self, system: str, prompt: str) -> str:
        self.calls.append(prompt)
        if len(self.calls) == 1:
            return prompt.replace("https://example.com/bench", "our benchmark page")
        return prompt


def test_repair_replaces_the_paragraph_instead_of_duplicating_it(usage, settings):
    from conftest import FakeAuth
    from fastapi.testclient import TestClient

    from declaude.app import create_app

    model = RewordingModel()
    client = TestClient(create_app(model=model, auth=FakeAuth(), usage=usage, settings=settings))
    text = "Great question! Here is the intro.\n\nResults live at https://example.com/bench for review."
    out = client.post("/v1/translate", json={"text": text}, headers=AUTH).json()["translation"]

    assert "https://example.com/bench" in out
    assert out.count("Results live at") == 1, "the reworded paragraph must be replaced, not duplicated"
    assert len([p for p in out.split("\n\n") if p.strip()]) == 2

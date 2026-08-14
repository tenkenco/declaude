"""Landing page: public, single-file HTML served at GET /."""


def test_root_returns_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")


def test_root_requires_no_auth(client):
    # No Authorization header at all — must still be public.
    r = client.get("/", headers={})
    assert r.status_code == 200


def test_root_mentions_product_and_endpoints(client):
    body = client.get("/").text
    assert "declaude" in body
    assert "/mcp" in body
    assert "/v1/translate" in body


def test_root_has_quickstart_and_pricing(client):
    body = client.get("/").text
    assert "claude mcp add" in body
    assert "$5" in body
    assert "github.com/tenkenco/declaude" in body


def test_root_is_lightweight(client):
    assert len(client.get("/").content) < 15 * 1024


def test_landing_uses_canonical_domain_not_run_app(client):
    html = client.get("/").text
    assert "speak-english.tenken.co" in html
    assert "run.app" not in html  # raw Cloud Run URLs must never appear in marketing copy


def test_page_does_not_pile_up_em_dashes(client):
    """The page that mocks em-dash pileups may not contain one."""
    import re

    body = re.sub(r"<(script|style)[\s\S]*?</\1>", "", client.get("/").text)
    text = re.sub(r"<[^>]+>", " ", body)
    assert text.count("\u2014") <= 1, f"{text.count(chr(8212))} em-dashes in landing copy"


def test_demo_hint_states_a_real_number(client):
    html = client.get("/").text
    assert "10 a day" in html
    assert "a few tries" not in html

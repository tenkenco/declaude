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


def test_root_links_to_signin(client):
    """Users must have a route to a key; the landing page is the only entry point."""
    assert 'href="/signin"' in client.get("/").text


def test_root_is_lightweight(client):
    assert len(client.get("/").content) < 15 * 1024

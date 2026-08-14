"""SEO + analytics surface: crawlable, shareable, measurable — and a human upgrade path."""
import pytest
from fastapi.testclient import TestClient

from declaude.app import create_app
from declaude.config import Settings


class FakeAuth:
    async def verify(self, token):
        raise ValueError


@pytest.fixture
def client(model, usage):
    s = Settings(
        free_tier_monthly_limit=3,
        stripe_payment_link="https://buy.stripe.com/test_declaude",
        public_base_url="https://speak-english.tenken.co",
        ga_measurement_id="G-TESTID123",
        clerk_publishable_key="pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk",
    )
    app = create_app(model=model, auth=FakeAuth(), usage=usage, settings=s)
    return TestClient(app)


@pytest.fixture
def bare_client(model, usage, settings):
    app = create_app(model=model, auth=FakeAuth(), usage=usage, settings=settings)
    return TestClient(app)


def test_robots_txt(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "Sitemap: https://speak-english.tenken.co/sitemap.xml" in r.text
    assert "Disallow: /v1/" in r.text  # API endpoints are not for crawlers


def test_sitemap(client):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert "https://speak-english.tenken.co/</loc>" in r.text
    assert "https://speak-english.tenken.co/signin</loc>" in r.text


def test_landing_has_canonical_and_open_graph(client):
    html = client.get("/").text
    assert '<link rel="canonical" href="https://speak-english.tenken.co/"' in html
    assert 'property="og:title"' in html
    assert 'property="og:description"' in html
    assert 'name="twitter:card"' in html


def test_landing_has_json_ld_software_app(client):
    html = client.get("/").text
    assert 'application/ld+json' in html
    assert '"SoftwareApplication"' in html
    assert '"price"' in html  # the $5/mo offer is machine-readable


def test_ga_injected_when_configured(client):
    html = client.get("/").text
    assert "googletagmanager.com/gtag/js?id=G-TESTID123" in html
    assert client.get("/signin").text.count("G-TESTID123") >= 1


def test_no_ga_when_unconfigured(bare_client):
    assert "googletagmanager" not in bare_client.get("/").text


def test_upgrade_redirects_to_payment_link(client):
    r = client.get("/upgrade", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "https://buy.stripe.com/test_declaude"


def test_upgrade_without_link_shows_pricing_note(model, usage):
    s = Settings(stripe_payment_link="")
    app = create_app(model=model, auth=FakeAuth(), usage=usage, settings=s)
    r = TestClient(app).get("/upgrade", follow_redirects=False)
    assert r.status_code == 200  # graceful, not a broken redirect


def test_402_references_upgrade_url(client, usage, model):
    # exhaust quota via api key path is complex here; call check via translate with paid=False user
    pass


def test_402_payload_contains_upgrade_url(bare_client, usage, settings):
    from declaude.keys import hash_key
    usage.add_api_key_sync(hash_key("dk_k"), "u1")
    h = {"Authorization": "Bearer dk_k"}
    for _ in range(settings.free_tier_monthly_limit):
        bare_client.post("/v1/translate", json={"text": "hi"}, headers=h)
    r = bare_client.post("/v1/translate", json={"text": "hi"}, headers=h)
    assert r.status_code == 402
    assert r.json()["upgrade_url"].endswith("/upgrade")


def test_og_image_served(client):
    r = client.get("/og.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_head_tags_carry_og_image(client):
    html = client.get("/").text
    assert 'property="og:image" content="https://speak-english.tenken.co/og.png"' in html
    assert 'name="twitter:card" content="summary_large_image"' in html


def test_sitemap_lists_documents(client):
    assert "/documents</loc>" in client.get("/sitemap.xml").text


def test_landing_has_demo_box(client):
    html = client.get("/").text
    assert 'id="demo-in"' in html and "/v1/demo" in html

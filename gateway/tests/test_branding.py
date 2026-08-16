"""Every page a signed-out visitor can reach should say who built declaude.

The Clerk card is titled "Sign in to Tenken" — the Clerk application name. Someone who clicked
"get an API key" on declaude has never seen that word before, so the page around the widget has
to account for it rather than leave the visitor guessing whose login screen they landed on.
"""
import re

import pytest

from declaude.documents_page import documents_html
from declaude.landing import LANDING_HTML
from declaude.oauth_page import authorize_html
from declaude.signin import signin_html

PK = "pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk"
JS = "https://clerk.example.com/clerk.js"

PAGES = {
    "landing": LANDING_HTML,
    "signin": signin_html(PK, JS),
    "authorize": authorize_html(PK, JS, "Claude Code"),
    "documents": documents_html(PK, JS),
}


@pytest.mark.parametrize("name", sorted(PAGES))
def test_page_names_its_maker(name):
    assert "Tenken" in PAGES[name], f"{name}: does not say who built it"


# Matched as a full href rather than a substring: a bare `"https://www.tenken.co" in html`
# check would pass on a link to tenken.co.evil.example and CodeQL rightly flags the pattern.
TENKEN_LINK = re.compile(r'href="https://www\.tenken\.co/?"')


@pytest.mark.parametrize("name", sorted(PAGES))
def test_maker_is_linked(name):
    assert TENKEN_LINK.search(PAGES[name]), f"{name}: Tenken is named but not linked"


@pytest.mark.parametrize("name", ["signin", "authorize"])
def test_clerk_pages_explain_the_name_on_the_widget(name):
    """The widget says "Sign in to Tenken"; the page must connect that to declaude."""
    html = PAGES[name]
    marker = html[html.find("Tenken") - 400 : html.find("Tenken") + 200]
    assert "declaude" in marker, f"{name}: Tenken appears without tying it to declaude"

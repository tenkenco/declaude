"""Regression: the Clerk widget must be centered on every page that mounts it.

Found by screenshotting the live sign-in page: the card sat 120px left of centre. The CSS
centered `#clerk > div`, but Clerk mounts its root box *onto* `#clerk` itself and shrink-wraps
it, so the rule never matched anything and the shrink-wrapped root sat at the container's left
edge. The rule has to apply to `#clerk`, and `#clerk` has to be full width for centering to mean
anything.
"""
import re

import pytest

from declaude.documents_page import documents_html
from declaude.oauth_page import authorize_html
from declaude.signin import signin_html

PK = "pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk"


def _rules_for_clerk_mount(html: str) -> str:
    """Every CSS block whose selector list targets #clerk itself (not a descendant)."""
    blocks = re.findall(r"([^{}]*)\{([^{}]*)\}", html)
    out = []
    for selector, body in blocks:
        for one in selector.split(","):
            one = one.strip().split("\n")[-1].strip()
            if one == "#clerk":
                out.append(body)
    return " ".join(out)


PAGES = {
    "signin": signin_html(PK, "https://clerk.example.com/clerk.js"),
    "authorize": authorize_html(PK, "https://clerk.example.com/clerk.js", "Claude Code"),
    "documents": documents_html(PK, "https://clerk.example.com/clerk.js"),
}


@pytest.mark.parametrize("name", sorted(PAGES))
def test_clerk_mount_is_centered(name):
    rules = _rules_for_clerk_mount(PAGES[name])
    assert rules, f"{name}: no CSS rule targets #clerk itself"
    assert "justify-content:center" in rules.replace(" ", ""), f"{name}: mount is not centered"
    assert "width:100%" in rules.replace(" ", ""), f"{name}: a shrink-wrapped mount cannot center"


@pytest.mark.parametrize("name", sorted(PAGES))
def test_clerk_mount_element_exists(name):
    assert 'id="clerk"' in PAGES[name]

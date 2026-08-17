"""The registry manifests must keep matching the service they advertise.

server.json and .claude-plugin/*.json are read by machines we do not control — the MCP registry,
Smithery, PulseMCP, the Claude Code plugin installer. A stale URL or an over-long description is
a listing that silently fails or never appears, and nothing in the app would notice.
"""
import json
from pathlib import Path

import pytest

from declaude.config import Settings

ROOT = Path(__file__).resolve().parents[2]
SERVER = json.loads((ROOT / "server.json").read_text())
PLUGIN = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
MARKET = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())


def test_server_json_advertises_the_real_mcp_endpoint():
    expected = Settings().public_base_url.rstrip("/") + "/mcp"
    assert SERVER["remotes"][0]["url"] == expected, "registry would point clients at the wrong host"
    assert SERVER["remotes"][0]["type"] == "streamable-http"


def test_server_name_is_reverse_dns_with_one_slash():
    """Registry rule: exactly one '/' separating namespace from name."""
    assert SERVER["name"].count("/") == 1
    namespace, _, name = SERVER["name"].partition("/")
    assert namespace == "io.github.tenkenco", "namespace must match the GitHub org that verifies it"
    assert name == "declaude"


def test_server_description_fits_the_registry_limit():
    """maxLength is 100 in the published schema; a longer one is rejected at submission."""
    assert len(SERVER["description"]) <= 100


def test_server_json_declares_the_schema_it_was_validated_against():
    assert SERVER["$schema"].startswith("https://static.modelcontextprotocol.io/schemas/")


@pytest.mark.parametrize("doc", [SERVER, PLUGIN])
def test_manifests_point_at_this_repository(doc):
    repo = doc["repository"]
    url = repo["url"] if isinstance(repo, dict) else repo
    assert url == "https://github.com/tenkenco/declaude"


def test_marketplace_lists_the_plugin_from_the_repo_root():
    entry = next(p for p in MARKET["plugins"] if p["name"] == "declaude")
    assert entry["source"] == "./", "install is `/plugin marketplace add tenkenco/declaude`"
    assert PLUGIN["name"] == entry["name"], "plugin.json and marketplace.json must agree on the name"


def test_plugin_ships_the_skill_that_makes_it_useful():
    """Installing the plugin is only worth anything if the skill comes with it."""
    assert (ROOT / "skills" / "declaude" / "SKILL.md").is_file()


def test_versions_are_semver():
    for doc in (SERVER, PLUGIN):
        parts = doc["version"].split(".")
        assert len(parts) == 3 and all(p.isdigit() for p in parts), doc["version"]

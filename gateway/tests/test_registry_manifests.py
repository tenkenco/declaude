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
HOOKS = json.loads((ROOT / "hooks" / "hooks.json").read_text())["hooks"]
SETUP_SKILL = (ROOT / "skills" / "setup" / "SKILL.md").read_text()


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


def test_server_json_matches_what_is_actually_published():
    """The registry already lists this server. If the file drifts from the live record, the next
    publish silently rewrites a listing that is working — so keep them identical by construction.

    Live record: https://registry.modelcontextprotocol.io/v0/servers?search=declaude
    """
    assert SERVER["title"] == "declaude"
    assert SERVER["version"] == "1.0.0"
    assert SERVER["$schema"].endswith("/2025-12-11/server.schema.json"), (
        "published under the 2025-12-11 schema; bumping this file without republishing splits them"
    )


def test_plugin_registers_the_hook_on_install():
    """The hook is the reason most people install this. Registering it here is what turns a
    manual settings.json edit into one `/plugin install`."""
    assert "MessageDisplay" in HOOKS
    entries = HOOKS["MessageDisplay"][0]["hooks"]
    assert [e["type"] for e in entries] == ["command"]


def test_plugin_registers_exactly_one_hook_event():
    """Two events means every reply is translated twice and billed twice."""
    assert set(HOOKS) == {"MessageDisplay"}, "Stop and MessageDisplay together double the bill"
    assert len(HOOKS["MessageDisplay"]) == 1


def test_hook_command_runs_the_script_that_ships_with_the_plugin():
    handler = HOOKS["MessageDisplay"][0]["hooks"][0]
    assert handler["command"] == "python3"
    assert handler["args"] == [
        "${CLAUDE_PLUGIN_ROOT}/hook/declaude_hook.py",
        "--plugin",
    ], "exec form passes plugin paths safely without shell quoting"
    assert (ROOT / "hook" / "declaude_hook.py").is_file()


def test_hook_timeout_survives_a_cold_gpu():
    """MessageDisplay defaults to a 10 second timeout. A spot reclaim wakes the GPU slower."""
    assert HOOKS["MessageDisplay"][0]["hooks"][0]["timeout"] >= 30


def test_hooks_are_declared_in_one_place_only():
    """hooks/hooks.json is loaded by its location. Naming it in plugin.json as well risks
    registering the same hook twice, which bills every reply twice."""
    assert "hooks" not in PLUGIN


def test_plugin_ships_the_setup_skill():
    """Registration is half the job; setup safely opts into the paid hook."""
    assert (ROOT / "skills" / "setup" / "SKILL.md").is_file()


def test_plugin_configuration_rewrites_by_default_and_secures_the_key():
    """The hook treats an unset switch as enabled. Do not declare a manifest
    default: exporting an implicit true would defeat the legacy-token guard."""
    options = PLUGIN["userConfig"]
    assert options["hook_enabled"]["type"] == "boolean"
    assert "default" not in options["hook_enabled"]
    assert options["api_key"]["type"] == "string"
    assert options["api_key"]["sensitive"] is True
    assert "required" not in options["api_key"], "a required key blocks MCP-only users"


def test_setup_requires_opt_in_without_replacing_an_existing_key():
    assert "/plugin configure declaude@tenken" in SETUP_SKILL
    assert "do not edit or replace it" in SETUP_SKILL.lower()

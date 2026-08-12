"""MCP server surface: JSON-RPC 2.0 over HTTP at /mcp, exposing the translate tool."""
from conftest import AUTH


def rpc(client, method, params=None, id=1):
    return client.post("/mcp", json={"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}}, headers=AUTH)


def test_initialize(client):
    r = rpc(client, "initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}})
    assert r.status_code == 200
    result = r.json()["result"]
    assert result["serverInfo"]["name"] == "declaude"
    assert "tools" in result["capabilities"]


def test_tools_list_exposes_translate(client):
    r = rpc(client, "tools/list")
    tools = r.json()["result"]["tools"]
    names = [t["name"] for t in tools]
    assert "translate" in names
    tool = next(t for t in tools if t["name"] == "translate")
    assert "text" in tool["inputSchema"]["properties"]


def test_tools_call_translate(client):
    r = rpc(client, "tools/call", {"name": "translate", "arguments": {"text": "Great question!"}})
    result = r.json()["result"]
    assert result["content"][0]["text"] == "PLAIN::Great question!"
    assert result["isError"] is False


def test_tools_call_unknown_tool_is_error(client):
    r = rpc(client, "tools/call", {"name": "nope", "arguments": {}})
    assert "error" in r.json()


def test_mcp_requires_auth(client):
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status_code == 401


def test_mcp_call_counts_against_quota(client, usage, settings):
    for _ in range(settings.free_tier_monthly_limit):
        rpc(client, "tools/call", {"name": "translate", "arguments": {"text": "hi"}})
    r = rpc(client, "tools/call", {"name": "translate", "arguments": {"text": "hi"}})
    assert r.status_code == 402

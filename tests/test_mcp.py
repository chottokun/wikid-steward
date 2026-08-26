from pathlib import Path

import pytest
from fastmcp import Client
from mcp.shared.exceptions import McpError

from wikid_steward.mcp.server import get_wiki_resource, mcp


@pytest.mark.anyio
async def test_mcp_resources_and_tools(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    sample_note = wiki_dir / "sample.md"
    sample_note.write_text(
        "---\ntitle: FastMCP Sample\ntype: Concept\n---\n\nFastMCP test content.",
        encoding="utf-8",
    )

    async with Client(mcp) as client:
        # Resource test
        res = await client.read_resource("wiki://sample.md")
        assert "FastMCP Sample" in str(res)

        # Tool test: lint
        lint_res = await client.call_tool("lint", {"dry_run": True})
        assert lint_res.content is not None

        # Tool test: moc
        moc_res = await client.call_tool("moc", {})
        assert moc_res.content is not None

        # Resource test: access denied via MCP client
        with pytest.raises(McpError, match="Access denied"):
            await client.read_resource("wiki://%2E%2E%2F%2E%2E%2Fetc%2Fpasswd")


def test_get_wiki_resource_access_denied(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    with pytest.raises(
        ValueError, match="Access denied: path '../../etc/passwd' is outside wiki directory"
    ):
        get_wiki_resource("../../etc/passwd")


def test_get_wiki_resource_not_found(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="Resource not found: nonexistent.md"):
        get_wiki_resource("nonexistent.md")

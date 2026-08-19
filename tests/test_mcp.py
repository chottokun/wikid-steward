from pathlib import Path

import pytest
from fastmcp import Client

from wikid_steward.mcp.server import mcp


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

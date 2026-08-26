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


def test_get_wiki_resource_success(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    sub_dir = wiki_dir / "docs"
    sub_dir.mkdir()
    file_path = sub_dir / "item.md"
    file_path.write_text("hello world", encoding="utf-8")

    from wikid_steward.mcp.server import get_wiki_resource

    content = get_wiki_resource("docs/item.md")
    assert content == "hello world"


def test_get_wiki_resource_path_traversal(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("super secret", encoding="utf-8")

    from wikid_steward.mcp.server import get_wiki_resource

    with pytest.raises(ValueError, match="Access denied"):
        get_wiki_resource("../secret.txt")


def test_get_wiki_resource_not_found(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    from wikid_steward.mcp.server import get_wiki_resource

    with pytest.raises(FileNotFoundError, match="Resource not found"):
        get_wiki_resource("non_existent.md")


def test_get_wiki_resource_is_directory(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "subfolder").mkdir()

    from wikid_steward.mcp.server import get_wiki_resource

    with pytest.raises(FileNotFoundError, match="Resource not found"):
        get_wiki_resource("subfolder")

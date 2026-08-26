from pathlib import Path

import pytest
from fastmcp import Client

from wikid_steward.mcp.server import get_wiki_resource, mcp


def test_get_wiki_resource_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    file_path = wiki_dir / "test_note.md"
    content = "# Test Note\nHello world!"
    file_path.write_text(content, encoding="utf-8")

    result = get_wiki_resource("test_note.md")
    assert result == content


def test_get_wiki_resource_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    # Case 1: File does not exist
    with pytest.raises(FileNotFoundError, match="Resource not found: non_existent.md"):
        get_wiki_resource("non_existent.md")

    # Case 2: Target path is a directory, not a file
    sub_dir = wiki_dir / "subfolder"
    sub_dir.mkdir()
    with pytest.raises(FileNotFoundError, match="Resource not found: subfolder"):
        get_wiki_resource("subfolder")


def test_get_wiki_resource_access_denied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    # Path traversal attempt outside wiki_dir
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("secret content", encoding="utf-8")

    with pytest.raises(
        ValueError, match="Access denied: path '../secret.txt' is outside wiki directory"
    ):
        get_wiki_resource("../secret.txt")


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

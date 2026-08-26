from pathlib import Path

from wikid_steward.core.moc_generator import generate_all_mocs, generate_moc_for_directory


def test_generate_moc_for_directory_root(tmp_path: Path) -> None:
    """Test generate_moc_for_directory when dir_path equals base_wiki_dir (Root Vault)."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir(parents=True)

    doc1 = wiki_dir / "doc1.md"
    doc1.write_text("---\ntitle: Document One\ntype: Note\n---\nBody text", encoding="utf-8")

    index_path = generate_moc_for_directory(wiki_dir, wiki_dir)

    assert index_path.exists()
    assert index_path.name == "index.md"

    content = index_path.read_text(encoding="utf-8")
    assert "# 🗺️ Map of Content: Root Vault" in content
    assert "全 1 件のドキュメントが登録されています。" in content
    assert "- [Document One](doc1.md) `[Note]`" in content


def test_generate_moc_for_directory_subdirectory(tmp_path: Path) -> None:
    """Test generate_moc_for_directory on a subdirectory."""
    wiki_dir = tmp_path / "wiki"
    sub_dir = wiki_dir / "ai" / "models"
    sub_dir.mkdir(parents=True)

    doc = sub_dir / "llm.md"
    doc.write_text(
        "---\ntitle: Large Language Model\ntype: Concept\n---\nContent", encoding="utf-8"
    )

    index_path = generate_moc_for_directory(sub_dir, wiki_dir)

    assert index_path.exists()
    content = index_path.read_text(encoding="utf-8")
    assert "# 🗺️ Map of Content: ai/models" in content
    assert "- [Large Language Model](llm.md) `[Concept]`" in content


def test_generate_moc_for_directory_file_filtering(tmp_path: Path) -> None:
    """Test that index.md and *.bak files are excluded from document entries."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir(parents=True)

    (wiki_dir / "doc1.md").write_text("---\ntitle: Doc 1\n---\nBody", encoding="utf-8")
    (wiki_dir / "doc2.md.bak").write_text("---\ntitle: Backup Doc\n---\nBody", encoding="utf-8")
    (wiki_dir / "index.md").write_text("# Existing index", encoding="utf-8")

    index_path = generate_moc_for_directory(wiki_dir, wiki_dir)
    content = index_path.read_text(encoding="utf-8")

    assert "全 1 件のドキュメントが登録されています。" in content
    assert "Doc 1" in content
    assert "Backup Doc" not in content


def test_generate_moc_for_directory_frontmatter_variants(tmp_path: Path) -> None:
    """Test frontmatter parsing variants: missing title/type, no frontmatter, empty YAML."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir(parents=True)

    # 1. No frontmatter -> title defaults to stem, type defaults to "Document"
    (wiki_dir / "a_no_fm.md").write_text(
        "# Plain text document\nNo frontmatter here.", encoding="utf-8"
    )

    # 2. Frontmatter missing title and type -> defaults applied
    (wiki_dir / "b_partial_fm.md").write_text("---\nauthor: Alice\n---\nBody", encoding="utf-8")

    # 3. Empty frontmatter -> yaml.safe_load returns None, defaults applied
    (wiki_dir / "c_empty_fm.md").write_text("---\n---\nBody", encoding="utf-8")

    index_path = generate_moc_for_directory(wiki_dir, wiki_dir)
    content = index_path.read_text(encoding="utf-8")

    assert "全 3 件のドキュメントが登録されています。" in content
    assert "- [a_no_fm](a_no_fm.md) `[Document]`" in content
    assert "- [b_partial_fm](b_partial_fm.md) `[Document]`" in content
    assert "- [c_empty_fm](c_empty_fm.md) `[Document]`" in content


def test_generate_moc_for_directory_sorting(tmp_path: Path) -> None:
    """Test document entries are sorted alphabetically by title."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir(parents=True)

    (wiki_dir / "file1.md").write_text("---\ntitle: Zebra\n---\nBody", encoding="utf-8")
    (wiki_dir / "file2.md").write_text("---\ntitle: Apple\n---\nBody", encoding="utf-8")
    (wiki_dir / "file3.md").write_text("---\ntitle: Mango\n---\nBody", encoding="utf-8")

    index_path = generate_moc_for_directory(wiki_dir, wiki_dir)
    content = index_path.read_text(encoding="utf-8")

    apple_idx = content.find("Apple")
    mango_idx = content.find("Mango")
    zebra_idx = content.find("Zebra")

    assert apple_idx < mango_idx < zebra_idx


def test_generate_all_mocs_non_existent_dir(tmp_path: Path) -> None:
    """Test generate_all_mocs with a non-existent directory."""
    non_existent = tmp_path / "does_not_exist"
    mocs = generate_all_mocs(non_existent)
    assert mocs == []


def test_generate_all_mocs_skips_assets(tmp_path: Path) -> None:
    """Test generate_all_mocs skips asset subdirectories."""
    wiki_dir = tmp_path / "wiki"
    topic_dir = wiki_dir / "topic"
    assets_dir = topic_dir / "assets"
    assets_dir.mkdir(parents=True)

    (topic_dir / "doc.md").write_text("---\ntitle: Topic Doc\n---\nBody", encoding="utf-8")
    (assets_dir / "ignore_me.md").write_text("---\ntitle: Asset Doc\n---\nBody", encoding="utf-8")

    mocs = generate_all_mocs(wiki_dir)

    moc_paths = [m.relative_to(wiki_dir).as_posix() for m in mocs]
    assert "index.md" in moc_paths
    assert "topic/index.md" in moc_paths
    assert "topic/assets/index.md" not in moc_paths

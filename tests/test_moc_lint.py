from pathlib import Path

from wikid_steward.core.linter import KnowledgeLinter
from wikid_steward.core.moc_generator import generate_all_mocs


def test_moc_generator_and_linter(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    llm_dir = wiki_dir / "llm"
    llm_dir.mkdir(parents=True)

    # 1. 正常なドキュメント作成
    doc_path = llm_dir / "paper1.md"
    doc_path.write_text(
        "---\nid: doc1\ntitle: Paper 1\ntype: Academic Paper\n---\n# Paper 1\n\nContent here.",
        encoding="utf-8",
    )

    # 2. MOC (index.md) 生成
    mocs = generate_all_mocs(wiki_dir)
    assert len(mocs) >= 1
    assert (llm_dir / "index.md").exists()

    index_content = (llm_dir / "index.md").read_text(encoding="utf-8")
    assert "Map of Content" in index_content
    assert "Paper 1" in index_content

    # 3. Linter の実行 (健全チェック)
    linter = KnowledgeLinter(wiki_dir)
    report = linter.run_lint()

    assert report.total_files >= 2  # paper1.md + index.md
    assert report.is_healthy is True


def test_linter_detects_broken_links_and_missing_frontmatter(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir(parents=True)

    # 不正なドキュメント (Frontmatter 欠損 ＆ 壊れた画像リンク)
    bad_doc = wiki_dir / "bad.md"
    bad_doc.write_text(
        "# Bad Document\n\nHere is a broken image: ![img](assets/missing.png)",
        encoding="utf-8",
    )

    linter = KnowledgeLinter(wiki_dir)
    report = linter.run_lint()

    assert report.is_healthy is False
    issue_types = [issue.issue_type for issue in report.issues]
    assert "MISSING_FRONTMATTER" in issue_types
    assert "BROKEN_IMAGE_LINK" in issue_types

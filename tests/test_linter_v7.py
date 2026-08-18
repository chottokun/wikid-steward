from pathlib import Path

from wikid_steward.core.linter import KnowledgeLinter


def test_linter_stub_creation_and_typo_suggest(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    concepts_dir = wiki_dir / "concepts"
    concepts_dir.mkdir()
    stubs_dir = wiki_dir / "stubs"

    # 1. 既存の正常ノート
    existing_note = concepts_dir / "system-architecture.md"
    existing_note.write_text(
        """---
type: Concept
title: システムアーキテクチャ
status: stable
---

# システムアーキテクチャ
システム全体の設計。
""",
        encoding="utf-8",
    )

    # 2. 参照元ノート（未定義の「システムアーキてくちゃ」と「全く新しい用語」へのリンクを含む）
    referencing_note = concepts_dir / "overview.md"
    referencing_note.write_text(
        """---
type: Concept
title: 概要
status: stable
---

# 概要
[[システムアーキてくちゃ]]（タイポ）と [[全く新しい用語]] を参照。
""",
        encoding="utf-8",
    )

    linter = KnowledgeLinter(wiki_dir)
    # dry_run=False でスタブ自動生成
    report = linter.run_lint(auto_create_stubs=True)

    # タイポ警告（サジェスト）が含まれているか
    typo_issues = [i for i in report.issues if i.issue_type == "TYPO_SUGGESTION"]
    assert len(typo_issues) >= 1
    assert "システムアーキテクチャ" in typo_issues[0].message

    # ファイル本文のリンクが勝手に書き換えられていないことの検証（安全策）
    assert "[[システムアーキてくちゃ]]" in referencing_note.read_text(encoding="utf-8")

    # 未定義リンクに対するスタブが wiki/stubs/ に作成されているか
    assert stubs_dir.exists()
    stub_files = list(stubs_dir.glob("*.md"))
    [f.stem for f in stub_files]
    assert len(stub_files) >= 1

    # スタブファイルの内容（OKF v0.2 & 手書きメモ）を検証
    stub_content = stub_files[0].read_text(encoding="utf-8")
    assert "type: Concept" in stub_content
    assert "status: draft" in stub_content
    assert "wikid-steward/linter" in stub_content
    assert "<!-- HUMAN BEGIN -->" in stub_content
    assert "<!-- HUMAN END -->" in stub_content


def test_linter_footnote_and_source_integrity(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    # sources にない footnote を持つノート
    broken_note = wiki_dir / "note_with_orphan_footnote.md"
    broken_note.write_text(
        """---
type: Concept
title: 脚注テスト
status: stable
sources:
  - id: valid-source
    resource: /sources/valid.pdf
---

# 脚注テスト
これは有効な参照[^valid-source]ですが、これは未定義の参照[^undefined-source]です。
""",
        encoding="utf-8",
    )

    linter = KnowledgeLinter(wiki_dir)
    report = linter.run_lint(auto_create_stubs=False)

    footnote_issues = [i for i in report.issues if i.issue_type == "ORPHAN_FOOTNOTE"]
    assert len(footnote_issues) == 1
    assert "undefined-source" in footnote_issues[0].message

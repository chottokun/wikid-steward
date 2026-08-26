from pathlib import Path
from unittest.mock import MagicMock

import pytest

from wikid_steward.core.okf_converter import parse_okf_frontmatter
from wikid_steward.core.resolver import resolve_git_conflict
from wikid_steward.core.reviewer import review_file


def test_review_file_not_found(tmp_path: Path):
    non_existent = tmp_path / "missing.md"
    with pytest.raises(FileNotFoundError, match="File not found"):
        review_file(non_existent)


def test_review_file_and_promote(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    stubs_dir = wiki_dir / "stubs"
    stubs_dir.mkdir()
    concepts_dir = wiki_dir / "concepts"
    concepts_dir.mkdir()

    stub_file = stubs_dir / "system-architecture.md"
    stub_file.write_text(
        """---
type: Concept
title: システムアーキテクチャ
status: draft
---

# システムアーキテクチャ
システム全体の設計。
""",
        encoding="utf-8",
    )

    promoted_file = review_file(stub_file, reviewer="human:chottokun", wiki_dir=wiki_dir)

    assert promoted_file.exists()
    assert not stub_file.exists()
    assert promoted_file.parent == concepts_dir

    meta, body = parse_okf_frontmatter(promoted_file)
    assert meta["status"] == "stable"
    assert len(meta["verified"]) >= 1
    assert meta["verified"][0]["by"] == "human:chottokun"


def test_review_file_in_place(tmp_path: Path):
    doc_file = tmp_path / "my_concept.md"
    doc_file.write_text(
        """---
type: Concept
title: 既存コンセプト
status: draft
---

# 既存コンセプト
既存ファイルのテスト。
""",
        encoding="utf-8",
    )

    result_path = review_file(doc_file, reviewer="human:reviewer1")

    assert result_path == doc_file.resolve()
    assert doc_file.exists()

    meta, body = parse_okf_frontmatter(doc_file)
    assert meta["status"] == "stable"
    assert len(meta["verified"]) == 1
    assert meta["verified"][0]["by"] == "human:reviewer1"


def test_review_file_metadata_preservation(tmp_path: Path):
    doc_file = tmp_path / "complex_doc.md"
    doc_file.write_text(
        """---
type: Pattern
title: 複合ドキュメント
status: draft
stale_after: 2026-12-31
tags:
  - architecture
  - design
generated:
  by: ai:compiler
  at: 2025-01-01T00:00:00Z
verified:
  - by: human:alice
    at: 2025-01-02T10:00:00Z
sources:
  - id: src-1
    resource: https://example.com/doc
    title: 参考ドキュメント
custom_key: custom_value
---

# 複合ドキュメント
詳細本文。
""",
        encoding="utf-8",
    )

    result_path = review_file(doc_file, reviewer="human:bob")

    meta, body = parse_okf_frontmatter(result_path)
    assert meta["type"] == "Pattern"
    assert meta["title"] == "複合ドキュメント"
    assert meta["status"] == "stable"
    assert str(meta["stale_after"]) == "2026-12-31"
    assert meta["tags"] == ["architecture", "design"]
    assert meta["generated"]["by"] == "ai:compiler"
    assert str(meta["generated"]["at"]).startswith("2025-01-01")

    # verified should have Alice and Bob
    assert len(meta["verified"]) == 2
    assert meta["verified"][0]["by"] == "human:alice"
    assert str(meta["verified"][0]["at"]).startswith("2025-01-02")
    assert meta["verified"][1]["by"] == "human:bob"

    # sources should be preserved
    assert len(meta["sources"]) == 1
    assert meta["sources"][0]["id"] == "src-1"
    assert meta["sources"][0]["resource"] == "https://example.com/doc"
    assert meta["sources"][0]["title"] == "参考ドキュメント"

    # custom metadata preserved
    assert meta["custom_key"] == "custom_value"


def test_review_file_promote_custom_target_dir(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    stubs_dir = wiki_dir / "stubs"
    stubs_dir.mkdir(parents=True)

    stub_file = stubs_dir / "pattern-a.md"
    stub_file.write_text(
        """---
type: Pattern
title: パターンA
status: draft
---

# パターンA
""",
        encoding="utf-8",
    )

    promoted_file = review_file(
        stub_file, reviewer="human:chottokun", wiki_dir=wiki_dir, target_dir_name="patterns"
    )

    assert promoted_file.exists()
    assert promoted_file.parent == wiki_dir / "patterns"
    assert not stub_file.exists()


def test_resolve_git_conflict(tmp_path: Path):
    conflict_file = tmp_path / "conflict.md"
    conflict_file.write_text(
        """---
type: Concept
title: コンフリクトテスト
status: stable
---

# コンフリクトテスト

<<<<<<< HEAD
人間が追記した内容A
=======
AIが更新した内容B
>>>>>>> steward/auto-compiler

## 📝 手書きメモ

<!-- HUMAN BEGIN -->
現場メモ: 衝突なし
<!-- HUMAN END -->
""",
        encoding="utf-8",
    )

    mock_llm = MagicMock()
    mock_llm.generate.return_value = "統合された内容（AとBの合体）"

    resolved = resolve_git_conflict(conflict_file, llm_client=mock_llm)
    assert resolved is True

    content = conflict_file.read_text(encoding="utf-8")
    assert "<<<<<<<" not in content
    assert "=======" not in content
    assert ">>>>>>>" not in content
    assert "現場メモ: 衝突なし" in content

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from wikid_steward.core.reviewer import review_file
from wikid_steward.core.resolver import resolve_git_conflict
from wikid_steward.core.okf_converter import parse_okf_frontmatter


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

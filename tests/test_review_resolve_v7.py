from pathlib import Path
from unittest.mock import MagicMock

import pytest

from wikid_steward.core.okf_converter import parse_okf_frontmatter
from wikid_steward.core.resolver import resolve_git_conflict
from wikid_steward.core.reviewer import review_file


def test_review_file_not_found(tmp_path: Path):
    non_existent = tmp_path / "non_existent.md"
    with pytest.raises(FileNotFoundError, match="File not found"):
        review_file(non_existent)


def test_review_file_non_stub_in_place(tmp_path: Path):
    doc_file = tmp_path / "regular_doc.md"
    doc_file.write_text(
        """---
type: Concept
title: Regular Document
status: draft
---

# Regular Document Content
""",
        encoding="utf-8",
    )

    result_file = review_file(doc_file, reviewer="human:alice")

    assert result_file == doc_file
    assert doc_file.exists()

    meta, body = parse_okf_frontmatter(doc_file)
    assert meta["status"] == "stable"
    assert len(meta["verified"]) == 1
    assert meta["verified"][0]["by"] == "human:alice"
    assert "# Regular Document Content" in body


def test_review_file_metadata_preservation(tmp_path: Path):
    doc_file = tmp_path / "existing_meta.md"
    doc_file.write_text(
        """---
type: Concept
title: Metadata Test
description: Test metadata preservation
status: draft
stale_after: 2027-01-01
generated:
  by: wikid-steward/auto-compiler
  at: 2026-01-01T00:00:00Z
verified:
  - by: human:bob
    at: 2026-01-02T00:00:00Z
sources:
  - id: source-1
    resource: /docs/spec.pdf
    title: Spec PDF
tags:
  - architecture
  - test
custom_field: custom_value
---

# Body
""",
        encoding="utf-8",
    )

    result_file = review_file(doc_file, reviewer="human:charlie")

    meta, body = parse_okf_frontmatter(result_file)
    assert meta["type"] == "Concept"
    assert meta["title"] == "Metadata Test"
    assert meta["description"] == "Test metadata preservation"
    assert meta["status"] == "stable"
    assert str(meta["stale_after"]) == "2027-01-01"
    assert meta["generated"]["by"] == "wikid-steward/auto-compiler"

    assert len(meta["verified"]) == 2
    assert meta["verified"][0]["by"] == "human:bob"
    assert meta["verified"][1]["by"] == "human:charlie"

    assert len(meta["sources"]) == 1
    assert meta["sources"][0]["id"] == "source-1"
    assert meta["sources"][0]["resource"] == "/docs/spec.pdf"
    assert meta["sources"][0]["title"] == "Spec PDF"

    assert meta["tags"] == ["architecture", "test"]
    assert meta["custom_field"] == "custom_value"


def test_review_file_stub_defaults_and_custom_target(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    stubs_dir = wiki_dir / "stubs"
    stubs_dir.mkdir(parents=True)

    stub_file = stubs_dir / "stub-doc.md"
    stub_file.write_text(
        """---
type: Concept
title: Stub Document
---

# Stub Content
""",
        encoding="utf-8",
    )

    # Calling review_file without explicit reviewer and wiki_dir, using custom target_dir_name
    promoted_file = review_file(stub_file, target_dir_name="custom_concepts")

    expected_target = wiki_dir / "custom_concepts" / "stub-doc.md"
    assert promoted_file == expected_target
    assert promoted_file.exists()
    assert not stub_file.exists()

    meta, body = parse_okf_frontmatter(promoted_file)
    assert meta["status"] == "stable"
    assert len(meta["verified"]) == 1
    assert meta["verified"][0]["by"] == "human:unknown"


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

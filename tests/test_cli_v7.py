import pytest
from click.testing import CliRunner
from pathlib import Path
from unittest.mock import patch, MagicMock
from wikid_steward.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "compile" in result.output
    assert "compile-stub" in result.output
    assert "review" in result.output
    assert "resolve" in result.output
    assert "lint" in result.output
    assert "search" in result.output
    assert "moc" in result.output


def test_cli_lint_and_review(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    concepts_dir = wiki_dir / "concepts"
    concepts_dir.mkdir()

    note = concepts_dir / "sample.md"
    note.write_text(
        """---
type: Concept
title: サンプル
status: draft
---

# サンプル
[[未定義概念]] を参照。
""",
        encoding="utf-8",
    )

    runner = CliRunner()
    # 1. lint 実行（スタブ起票）
    result_lint = runner.invoke(main, ["lint", "--dir", str(tmp_path)])
    assert result_lint.exit_code == 0
    assert "wiki/stubs/" in result_lint.output

    stubs = list((wiki_dir / "stubs").glob("*.md"))
    assert len(stubs) == 1
    stub_file = stubs[0]

    # 2. review 実行
    result_review = runner.invoke(
        main,
        ["review", str(stub_file), "--reviewer", "human:tester", "--dir", str(tmp_path)],
    )
    assert result_review.exit_code == 0
    assert "Verified by 'human:tester'" in result_review.output
    # stubs から concepts に昇格されているか
    assert not stub_file.exists()
    assert (concepts_dir / stub_file.name).exists()

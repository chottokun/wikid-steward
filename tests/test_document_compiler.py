from pathlib import Path
import pytest

from wikid_steward.core.config import AppConfig, get_config
from wikid_steward.core.document_compiler import DocumentToOKFCompiler, CompilationResult
from wikid_steward.core.okf_converter import parse_okf_frontmatter


@pytest.fixture
def temp_workspace(tmp_path: Path):
    """テスト用の一時ワークスペースディレクトリ構造を初期化するフィクスチャ"""
    raw_dir = tmp_path / "_raw"
    sources_dir = tmp_path / "raw_sources"
    wiki_dir = tmp_path / "wiki"
    concepts_dir = tmp_path / "wiki" / "concepts"
    stubs_dir = tmp_path / "wiki" / "stubs"
    staging_dir = tmp_path / "staging"

    for d in [raw_dir, sources_dir, wiki_dir, concepts_dir, stubs_dir, staging_dir]:
        d.mkdir(parents=True, exist_ok=True)

    return tmp_path


def test_compile_plain_markdown_to_okf_notes(temp_workspace: Path):
    """プレーンMarkdownドキュメントから _raw/ の生MD、wiki/ のメインノート、wiki/concepts/ の用語ノート群がOKF v0.2形式で生成されることを検証"""
    sample_doc = temp_workspace / "sample_architecture.md"
    sample_content = """# マイクロサービス設計仕様書

本仕様書は、分散トレーシングおよびイベント駆動アーキテクチャの基本設計を定義する。

## イベント駆動アーキテクチャ
イベント駆動アーキテクチャは、疎結合なサービス間連携を実現する。

## 分散トレーシング
分散トレーシングにより、リクエストのエンドツーエンドの可視性を確保する。
"""
    sample_doc.write_text(sample_content, encoding="utf-8")

    compiler = DocumentToOKFCompiler(base_dir=temp_workspace)
    result = compiler.compile_file(
        file_path=sample_doc,
        status="draft",
        save_source=True,
        extract_terms=True,
    )

    assert isinstance(result, CompilationResult)

    # 1. _raw/{slug}.md に OKF フロントマター付きの生Markdownが保存されていること
    assert result.raw_markdown_path.exists()
    raw_fm, raw_body = parse_okf_frontmatter(result.raw_markdown_path)
    assert raw_fm.get("type") in ["Source", "Raw Document"]
    assert "マイクロサービス設計仕様書" in raw_body or "分散トレーシング" in raw_body
    assert "sources" in raw_fm

    # 2. wiki/ 配下にメインノートが生成されていること
    assert result.main_note_path.exists()
    main_fm, main_body = parse_okf_frontmatter(result.main_note_path)
    assert main_fm.get("status") == "draft"
    assert "## 📝 手書きメモ" in main_body
    assert "<!-- HUMAN BEGIN -->" in main_body
    assert "<!-- HUMAN END -->" in main_body

    # 3. 原本ファイルが sources/ (または raw_sources/) に保存されていること
    assert result.saved_source_path is not None
    assert result.saved_source_path.exists()


def test_compile_with_status_stable_and_reviewer(temp_workspace: Path):
    """status: stable オプションおよび reviewer 指定時に、即座に stable ステータスと verified ログが付与されることを検証"""
    sample_doc = temp_workspace / "stable_spec.md"
    sample_doc.write_text("# 確定仕様書\n\n確定した仕様内容。", encoding="utf-8")

    compiler = DocumentToOKFCompiler(base_dir=temp_workspace)
    result = compiler.compile_file(
        file_path=sample_doc,
        status="stable",
        reviewer="human:nobuhiko",
        save_source=False,
    )

    main_fm, _ = parse_okf_frontmatter(result.main_note_path)
    assert main_fm.get("status") == "stable"
    assert "verified" in main_fm
    assert any(v.get("by") == "human:nobuhiko" for v in main_fm["verified"])

    # save_source=False なので保存されていないこと
    assert result.saved_source_path is None


def test_compile_with_hide_source_links(temp_workspace: Path):
    """hide_source_links=True 時に、フロントマターや本文に原本の実ファイルパスが露出しないことを検証"""
    sample_doc = temp_workspace / "secret_document.md"
    sample_doc.write_text("# 社外秘資料\n\n機密情報の内容。", encoding="utf-8")

    compiler = DocumentToOKFCompiler(base_dir=temp_workspace)
    result = compiler.compile_file(
        file_path=sample_doc,
        hide_source_links=True,
    )

    main_fm, main_body = parse_okf_frontmatter(result.main_note_path)
    sources = main_fm.get("sources", [])
    for s in sources:
        assert str(sample_doc) not in s.get("resource", "")
    assert str(sample_doc) not in main_body


def test_cli_compile_command(temp_workspace: Path):
    """CLI wikid-steward compile コマンドの正常実行を検証"""
    from click.testing import CliRunner
    from wikid_steward.cli import main

    sample_doc = temp_workspace / "cli_test_doc.md"
    sample_doc.write_text("# CLIテスト文書\n\nこれはCLI経由でのコンパイルテスト。", encoding="utf-8")

    runner = CliRunner()
    res = runner.invoke(
        main,
        [
            "compile",
            str(sample_doc),
            "--dir",
            str(temp_workspace),
            "--auto-stable",
            "--reviewer",
            "human:tester",
        ],
    )
    assert res.exit_code == 0
    assert "Compilation finished" in res.output

    # 生成されたファイルの検証
    compiled_main = temp_workspace / "wiki" / "cli_test_doc.md"
    assert compiled_main.exists()
    fm, _ = parse_okf_frontmatter(compiled_main)
    assert fm.get("status") == "stable"
    assert any(v.get("by") == "human:tester" for v in fm.get("verified", []))


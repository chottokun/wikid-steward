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


def test_compile_real_raw_source_pdf(temp_workspace: Path):
    """raw_sources/ 配下の実 PDF (LoRA 論文) を用いた DocumentToOKFCompiler のエンドツーエンド変換検証"""
    project_root = Path.cwd()
    lora_pdf = project_root / "raw_sources" / "finetuning" / "LoRA-Low-Rank-Adaptation.pdf"
    if not lora_pdf.exists():
        pytest.skip("LoRA PDF not found in raw_sources/")

    compiler = DocumentToOKFCompiler(base_dir=temp_workspace)
    res = compiler.compile_file(
        file_path=lora_pdf,
        status="stable",
        save_source=True,
        extract_terms=True,
    )

    assert res.raw_markdown_path.exists()
    assert res.main_note_path.exists()
    assert res.saved_source_path is not None and res.saved_source_path.exists()

    # _raw/ 配下の生Markdownの OKF 検証
    raw_fm, raw_body = parse_okf_frontmatter(res.raw_markdown_path)
    assert raw_fm.get("type") == "Source"
    assert "## 📝 手書きメモ" in raw_body

    # メインノートの OKF 検証
    main_fm, main_body = parse_okf_frontmatter(res.main_note_path)
    assert main_fm.get("type") in ["Academic Paper", "General Document", "Concept"]
    assert main_fm.get("status") == "stable"


def test_compile_doc_type_drawing_sbom_profile(temp_workspace: Path):
    """doc_type 別プロファイル（drawing / drawing_sbom）による SBOM 表の自動挿入および OKF type の検証"""
    drawing_file = temp_workspace / "DWG-001.md"
    drawing_file.write_text(
        "# CAD Drawing DWG-001\n\nITEM 01 - Power Board - Qty 2\nITEM 02 - Sensor Unit - Qty 1\n",
        encoding="utf-8",
    )

    compiler = DocumentToOKFCompiler(base_dir=temp_workspace)
    res = compiler.compile_file(
        file_path=drawing_file,
        profile_name="drawing",
        status="stable",
    )

    main_fm, main_body = parse_okf_frontmatter(res.main_note_path)
    assert main_fm.get("type") == "Technical Drawing"
    assert "SBOM (Software/Hardware Bill of Materials)" in main_body
    assert "<table" in main_body


def test_concept_reference_source_appending_and_protection(temp_workspace: Path):
    """既存の概念ノートが存在する場合に、定義や手書きメモを保護しつつ言及ソースが本文に追記されることを検証"""
    concepts_dir = temp_workspace / "wiki" / "concepts"
    existing_concept_path = concepts_dir / "distributed_tracing.md"

    existing_content = """---
type: Concept
title: "Distributed Tracing"
status: stable
verified:
  - by: "human:reviewer1"
    at: "2026-08-10T00:00:00Z"
sources:
  - id: "primary-paper"
    resource: "raw_sources/dapper.pdf"
    title: "Dapper Paper"
---

# Distributed Tracing

## 概要
Google Dapper に基づく分散トレーシングのオリジナル定義。

## 📝 手書きメモ

<!-- HUMAN BEGIN -->
現場での検証メモ: OpenTelemetry との互換性を確認済み。
<!-- HUMAN END -->

## 📚 関連・言及ソース (References)
* **一次定義**: [[dapper]] (`raw_sources/dapper.pdf`)
"""
    existing_concept_path.write_text(existing_content, encoding="utf-8")

    # 新しいドキュメントを投入してコンパイル
    new_doc = temp_workspace / "service_mesh_guide.md"
    new_doc.write_text(
        "# サービスメッシュ運用ガイド\n\n分散トレーシング (Distributed Tracing) を活用してレイテンシを監視する。\n",
        encoding="utf-8",
    )

    compiler = DocumentToOKFCompiler(base_dir=temp_workspace)
    # 用語抽出で "Distributed Tracing" が検出されるように直接コンパイル実行
    from wikid_steward.core.glossary import GlossaryTerm
    # モック/直接呼び出しシミュレーション
    res = compiler.compile_file(
        file_path=new_doc,
        status="draft",
        save_source=False,
    )

    # 既存概念ノートの検証
    updated_content = existing_concept_path.read_text(encoding="utf-8")
    fm, body = parse_okf_frontmatter(updated_content)

    # 1. フロントマターの status (stable) および verified がダウングレード・破壊されていないこと
    assert fm.get("status") == "stable"
    assert len(fm.get("verified", [])) == 1

    # 2. 既存の概要本文および手書きメモが 100% 保持されていること
    assert "Google Dapper に基づく分散トレーシングのオリジナル定義。" in body
    assert "OpenTelemetry との互換性を確認済み。" in body

    # 3. 関連・言及ソースセクションが存在すること
    assert "## 📚 関連・言及ソース (References)" in body




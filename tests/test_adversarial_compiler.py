from pathlib import Path
from unittest.mock import MagicMock

import pytest

from wikid_steward.core.document_compiler import DocumentToOKFCompiler
from wikid_steward.core.linter import KnowledgeLinter
from wikid_steward.core.okf_converter import parse_okf_frontmatter


@pytest.fixture
def test_env(tmp_path: Path):
    """批判的テスト用の一時ディレクトリ環境"""
    raw_dir = tmp_path / "_raw"
    wiki_dir = tmp_path / "wiki"
    concepts_dir = tmp_path / "wiki" / "concepts"
    sources_dir = tmp_path / "raw_sources"
    for d in [raw_dir, wiki_dir, concepts_dir, sources_dir]:
        d.mkdir(parents=True, exist_ok=True)
    return tmp_path


# ==============================================================================
# 1. 破壊的・極端な入力に対する堅牢性テスト (Adversarial Inputs)
# ==============================================================================


def test_extreme_filename_and_emoji_handling(test_env: Path):
    """絵文字、連続記号、極端に長いファイル名、macOS濁点(NFD)混じりのファイルを安全に処理できるか検証"""
    weird_name = "🚀【最新版】!!__設計_仕様書 (v2.0) [超重要] #1 $&+.md"
    doc_path = test_env / weird_name
    doc_path.write_text("# 極端なファイル名テスト\n\n内容の検証。", encoding="utf-8")

    compiler = DocumentToOKFCompiler(base_dir=test_env)
    res = compiler.compile_file(file_path=doc_path, status="stable", extract_terms=False)

    assert res.raw_markdown_path.exists()
    assert res.main_note_path.exists()
    assert not any(
        c in res.main_note_path.name for c in [":", "*", "?", '"', "<", ">", "|", "#", "🚀"]
    )


def test_empty_and_corrupted_document_handling(test_env: Path):
    """0バイトの空ファイルや空白のみのファイルでもクラッシュせず安全にOKFノートを生成できるか検証"""
    empty_doc = test_env / "empty_doc.md"
    empty_doc.write_text("", encoding="utf-8")

    compiler = DocumentToOKFCompiler(base_dir=test_env)
    res = compiler.compile_file(file_path=empty_doc, extract_terms=True)

    assert res.raw_markdown_path.exists()
    assert res.main_note_path.exists()
    fm, body = parse_okf_frontmatter(res.main_note_path)
    assert fm.get("type") is not None
    assert "## 📝 手書きメモ" in body


# ==============================================================================
# 2. LLM 応答異常・JSON 破損時のフォールバック耐性テスト
# ==============================================================================


def test_corrupted_llm_json_response_resilience(test_env: Path):
    """LLM が壊れた JSON や意図しないプレーンテキストを返した場合でも、例外で落ちずにコンパイルを完遂できるか検証"""
    mock_llm = MagicMock()
    # 壊れた文字列や不正なマークダウンを返すシミュレーション
    mock_llm.generate_chat_completion.return_value = (
        "これはJSONではありません。```json {不正なJSON```"
    )

    doc_path = test_env / "resilience_test.md"
    doc_path.write_text("# 堅牢性テスト\n\nLLMの応答が壊れた場合の動作確認。", encoding="utf-8")

    compiler = DocumentToOKFCompiler(base_dir=test_env, llm_client=mock_llm)
    res = compiler.compile_file(file_path=doc_path, extract_terms=True)

    assert res.raw_markdown_path.exists()
    assert res.main_note_path.exists()
    assert isinstance(res.concept_note_paths, list)


# ==============================================================================
# 3. 冪等性（Idempotency）と手書きメモの100%保護テスト
# ==============================================================================


def test_repeated_compilation_idempotency_and_memo_preservation(test_env: Path):
    """同一ファイルを 5 回連続でコンパイルしても、手書きメモが破壊されず、言及ソースが重複増殖しないことを検証"""
    doc_path = test_env / "idempotency_spec.md"
    doc_path.write_text(
        "# 冪等性仕様書\n\n分散トランザクション (Distributed Transaction) の仕様。\n",
        encoding="utf-8",
    )

    compiler = DocumentToOKFCompiler(base_dir=test_env)

    # 1回目のコンパイル
    res1 = compiler.compile_file(file_path=doc_path, extract_terms=False)

    # 人間が手書きメモと本文を追記・推敲
    main_note = res1.main_note_path
    human_edited_content = main_note.read_text(encoding="utf-8").replace(
        "<!-- HUMAN BEGIN -->\n<!-- HUMAN END -->",
        "<!-- HUMAN BEGIN -->\n【現場検証メモ】2026-08-17: 2相コミットで正常動作を確認。\n<!-- HUMAN END -->",
    )
    main_note.write_text(human_edited_content, encoding="utf-8")

    # 2回目〜5回目の連続コンパイル実行
    for i in range(4):
        compiler.compile_file(file_path=doc_path, extract_terms=False)

    final_content = main_note.read_text(encoding="utf-8")

    # 手書きメモが失われていないこと
    assert "【現場検証メモ】2026-08-17: 2相コミットで正常動作を確認。" in final_content
    # 手書きメモセクションが重複増殖していないこと
    assert final_content.count("## 📝 手書きメモ") == 1
    assert final_content.count("<!-- HUMAN BEGIN -->") == 1


# ==============================================================================
# 4. 特殊構文（コードブロック・数式・HTMLテーブル・非標準タグ）の保護テスト
# ==============================================================================


def test_code_block_and_html_table_protection(test_env: Path):
    """コードブロック内のキーワードや HTML テーブル内のタグが WikiRelinker によって誤置換・破壊されないことを検証"""
    doc_path = test_env / "complex_syntax.md"
    content = r"""# 複雑な構文テスト

## コードブロック
```python
# ここに登場する Transformer や LoRA は WikiLink 化されてはならない
def transformer_model():
    return "LoRA"
```

## HTML テーブル
<table border="1">
  <tr><td rowspan="2"><b>LoRA Config</b></td><td>Rank: 8</td></tr>
  <tr><td>Alpha: 16</td></tr>
</table>

## 数式ブロック
$$
W = W_0 + \Delta W, \quad \Delta W = B \cdot A
$$
"""
    doc_path.write_text(content, encoding="utf-8")

    compiler = DocumentToOKFCompiler(base_dir=test_env)
    res = compiler.compile_file(file_path=doc_path, extract_terms=False)

    compiled_text = res.main_note_path.read_text(encoding="utf-8")

    # コードブロック内の保護確認
    assert "def transformer_model():" in compiled_text
    assert "[[" not in compiled_text.split("```python")[1].split("```")[0]

    # HTML テーブルの属性とタグの保護確認
    assert '<table border="1">' in compiled_text
    assert '<td rowspan="2">' in compiled_text

    # 数式ブロックの保護確認
    assert r"\Delta W = B \cdot A" in compiled_text


# ==============================================================================
# 5. 生成されたナレッジベース全体の静的健全性監査 (Linter Audit)
# ==============================================================================


def test_generated_wiki_knowledge_linter_health(test_env: Path):
    """コンパイルによって生成された Wiki ノート群が KnowledgeLinter の監査で Healthy と判定されることを検証"""
    sample_doc = test_env / "audit_target.md"
    sample_doc.write_text(
        "# 監査対象文書\n\nマイクロサービスアーキテクチャの定義。", encoding="utf-8"
    )

    compiler = DocumentToOKFCompiler(base_dir=test_env)
    compiler.compile_file(file_path=sample_doc, status="stable", extract_terms=False, auto_moc=True)

    linter = KnowledgeLinter(wiki_dir=test_env / "wiki")
    report = linter.run_lint(auto_create_stubs=False)

    # 致命的な問題（不正なYAML、予約名違反など）が0件であること
    assert report.total_files >= 1
    fatal_issues = [
        i for i in report.issues if i.issue_type in ["frontmatter_error", "corrupted_yaml"]
    ]
    assert len(fatal_issues) == 0

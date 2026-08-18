from pathlib import Path

from wikid_steward.core.human_memo import merge_human_memo
from wikid_steward.core.linter import KnowledgeLinter
from wikid_steward.core.relinker import (
    convert_gfm_to_wikilinks,
    convert_wikilinks_to_gfm,
)
from wikid_steward.core.retro_compiler import is_trusted_context_source


def test_tc1_typo_suggest_warning_only_without_correction(tmp_path: Path):
    """TC1: タイポ・表記ブレに対して警告のみを発行し、ファイル本文は自動訂正しない安全策"""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    concepts_dir = wiki_dir / "concepts"
    concepts_dir.mkdir()

    # 既存の正規ノート
    (concepts_dir / "system-architecture.md").write_text(
        """---
type: Concept
title: システムアーキテクチャ
status: stable
---

# システムアーキテクチャ
設計の根幹。
""",
        encoding="utf-8",
    )

    # タイポを含む参照元ノート
    overview_file = concepts_dir / "overview.md"
    overview_file.write_text(
        """---
type: Concept
title: 概要
status: stable
---

# 概要
[[システムアーキてくちゃ]] を参照してください。
""",
        encoding="utf-8",
    )

    linter = KnowledgeLinter(wiki_dir)
    report = linter.run_lint(auto_create_stubs=False)

    # 類似度0.75以上のタイポ候補がサジェスト警告されているか
    typo_issues = [i for i in report.issues if i.issue_type == "TYPO_SUGGESTION"]
    assert len(typo_issues) >= 1
    assert "システムアーキテクチャ" in typo_issues[0].message

    # 本文のリンクは勝手に書き換えられていないこと
    assert "[[システムアーキてくちゃ]]" in overview_file.read_text(encoding="utf-8")


def test_tc2_human_memo_absolute_protection():
    """TC2: 手書きメモ（<!-- HUMAN BEGIN --> ... <!-- HUMAN END -->）の絶対死守"""
    existing_file_content = """---
type: Concept
title: 実装メモ
status: stable
---

# 実装メモ
AIが生成した旧本文。

## 📝 手書きメモ

<!-- HUMAN BEGIN -->
【現場の最重要ノウハウ】
・本番環境ではパラメータXを必ず300に設定すること。
・障害対応時はログサーバーBを確認する。
<!-- HUMAN END -->
"""

    new_ai_generated_content = """---
type: Concept
title: 実装メモ
status: stable
---

# 実装メモ
AIが新しく再生成・自動合成した本文。

## 📝 手書きメモ

<!-- HUMAN BEGIN -->
<!-- HUMAN END -->

## 追加セクション
最新のAI分析結果。
"""

    merged = merge_human_memo(
        new_content=new_ai_generated_content,
        existing_content=existing_file_content,
    )

    # AI生成部が最新化されつつ、手書きメモ内のテキストは1文字も破壊されていないこと
    assert "AIが新しく再生成・自動合成した本文。" in merged
    assert "最新のAI分析結果。" in merged
    assert "【現場の最重要ノウハウ】" in merged
    assert "・本番環境ではパラメータXを必ず300に設定すること。" in merged
    assert "・障害対応時はログサーバーBを確認する。" in merged


def test_tc3_ai_anti_hallucination_filter():
    """TC3: AI循環コピーおよびハルシネーション連鎖の100%遮断"""
    # 1. 人間査読済み (採用可)
    assert (
        is_trusted_context_source(
            {
                "status": "draft",
                "generated": {"by": "wikid-steward/auto-compiler"},
                "verified": [{"by": "human:reviewer"}],
            }
        )
        is True
    )

    # 2. 人間が手書き (採用可)
    assert (
        is_trusted_context_source(
            {
                "status": "draft",
                "generated": {"by": "human:chottokun"},
            }
        )
        is True
    )

    # 3. 未検証のAIドラフト (100% 排除)
    assert (
        is_trusted_context_source(
            {
                "status": "draft",
                "generated": {"by": "wikid-steward/auto-compiler"},
            }
        )
        is False
    )


def test_tc4_gfm_portability_conversion():
    """TC4: GFM互換性と標準Markdownリンクへの双方向変換"""
    wiki_map = {
        "PID制御": "concepts/pid-control.md",
        "カルマンフィルタ": "concepts/kalman-filter.md",
    }
    wikilink_text = "制御系には [[PID制御]] および [[カルマンフィルタ|Kalman Filter]] を使用。"

    gfm_text = convert_wikilinks_to_gfm(wikilink_text, wiki_map, base_path="/wiki")
    assert "[PID制御](/wiki/concepts/pid-control.md)" in gfm_text
    assert "[Kalman Filter](/wiki/concepts/kalman-filter.md)" in gfm_text

    # 逆変換
    restored = convert_gfm_to_wikilinks(gfm_text)
    assert "[[PID制御]]" in restored
    assert "[[Kalman Filter]]" in restored


def test_tc5_footnotes_and_source_integrity(tmp_path: Path):
    """TC5: 脚注と Frontmatter sources の静的整合性スキャン"""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    broken_note = wiki_dir / "draft.md"
    broken_note.write_text(
        """---
type: Concept
title: ソース検証
status: draft
sources:
  - id: valid-doc
    resource: /sources/valid.pdf
---

# ソース検証
有効な引用[^valid-doc]と、未登録の孤立脚注[^unregistered-source]です。
""",
        encoding="utf-8",
    )

    linter = KnowledgeLinter(wiki_dir)
    report = linter.run_lint(auto_create_stubs=False)

    issues = [i for i in report.issues if i.issue_type == "ORPHAN_FOOTNOTE"]
    assert len(issues) == 1
    assert "unregistered-source" in issues[0].message

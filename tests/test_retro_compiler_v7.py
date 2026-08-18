from pathlib import Path
from unittest.mock import MagicMock

from wikid_steward.core.okf_converter import parse_okf_frontmatter
from wikid_steward.core.retro_compiler import (
    RetroCompiler,
    is_trusted_context_source,
)


def test_trusted_context_source_filtering():
    # 1. 人間査読済み (採用)
    fm1 = {
        "status": "draft",
        "generated": {"by": "wikid-steward/auto-compiler"},
        "verified": [{"by": "human:nobuhiko"}],
    }
    assert is_trusted_context_source(fm1) is True

    # 2. 人間が手書き (採用)
    fm2 = {"status": "draft", "generated": {"by": "human:nobuhiko"}}
    assert is_trusted_context_source(fm2) is True

    # 3. status: stable の AI生成物 (採用)
    fm3 = {"status": "stable", "generated": {"by": "wikid-steward/auto-compiler"}}
    assert is_trusted_context_source(fm3) is True

    # 4. status: draft かつ AI生成物で未査読 (排除・循環汚染防止)
    fm4 = {"status": "draft", "generated": {"by": "wikid-steward/auto-compiler"}}
    assert is_trusted_context_source(fm4) is False


def test_retro_compiler_trigger_and_synthesis(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    concepts_dir = wiki_dir / "concepts"
    concepts_dir.mkdir()
    stubs_dir = wiki_dir / "stubs"
    stubs_dir.mkdir()

    # スタブノート作成
    stub_file = stubs_dir / "pid-control.md"
    stub_file.write_text(
        """---
type: Concept
title: PID制御
status: draft
generated:
  by: wikid-steward/linter
---

# PID制御
※ スタブです。

## 📝 手書きメモ

<!-- HUMAN BEGIN -->
現場検証メモ: ゲイン調整に注意
<!-- HUMAN END -->
""",
        encoding="utf-8",
    )

    # 参照元ドキュメント1 (信頼できるソース: verified)
    doc1 = concepts_dir / "motor-control.md"
    doc1.write_text(
        """---
type: Concept
title: モーター制御
status: stable
verified:
  - by: human:nobuhiko
---

# モーター制御
モーターの回転数制御には [[PID制御]] を用いるのが一般的である。
""",
        encoding="utf-8",
    )

    # 参照元ドキュメント2 (信頼できるソース: stable)
    doc2 = concepts_dir / "temperature-control.md"
    doc2.write_text(
        """---
type: Concept
title: 温度制御
status: stable
---

# 温度制御
ヒーターのフィードバックには [[PID制御]] の積分項が重要となる。
""",
        encoding="utf-8",
    )

    # 参照元ドキュメント3 (信頼できるソース: human)
    doc3 = concepts_dir / "flight-control.md"
    doc3.write_text(
        """---
type: Concept
title: 飛行姿勢制御
status: draft
generated:
  by: human:nobuhiko
---

# 飛行姿勢制御
ドローンの姿勢安定化に [[PID制御]] アルゴリズムを適用する。
""",
        encoding="utf-8",
    )

    # 参照元ドキュメント4 (除外されるべきAIドラフト未査読ソース)
    doc4 = concepts_dir / "ai-draft.md"
    doc4.write_text(
        """---
type: Concept
title: AI下書き
status: draft
generated:
  by: wikid-steward/auto-compiler
---

# AI下書き
ハルシネーションの恐れがある [[PID制御]] の記述。
""",
        encoding="utf-8",
    )

    # Mock LLM Client
    mock_llm = MagicMock()
    mock_llm.generate.return_value = """## 概要
PID制御（比例・積分・微分制御）は、フィードバック制御において代表的な制御アルゴリズムである。

## 適用例
- モーターの回転数制御
- ヒーターの温度制御
- ドローンの姿勢安定化
"""

    compiler = RetroCompiler(wiki_dir=wiki_dir, min_backlinks=3, llm_client=mock_llm)

    # バックリンク収集
    backlinks = compiler.collect_backlinks_for_term("PID制御")
    # doc1, doc2, doc3 の3件が採用され、doc4 は除外されるはず
    assert len(backlinks) == 3
    doc_titles = [b.source_title for b in backlinks]
    assert "モーター制御" in doc_titles
    assert "温度制御" in doc_titles
    assert "飛行姿勢制御" in doc_titles
    assert "AI下書き" not in doc_titles

    # 逆合成と昇格の実行
    promoted_file = compiler.compile_stub("PID制御")
    assert promoted_file is not None
    assert promoted_file.exists()
    # wiki/stubs から wiki/concepts に昇格移動されているか
    assert not stub_file.exists()
    assert promoted_file.parent == concepts_dir

    content = promoted_file.read_text(encoding="utf-8")
    fm, body = parse_okf_frontmatter(content)
    assert fm["type"] == "Concept"
    assert fm["status"] == "stable"
    assert fm["generated"]["by"] == "wikid-steward/auto-compiler"
    # 手書きメモが保護・維持されているか
    assert "現場検証メモ: ゲイン調整に注意" in body
    assert "比例・積分・微分制御" in body

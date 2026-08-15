import pytest
from pathlib import Path
from unittest.mock import MagicMock
from wikid_steward.core.graph_searcher import LightweightGraphSearchEngine


def test_lightweight_graph_searcher(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    concepts_dir = wiki_dir / "concepts"
    concepts_dir.mkdir()

    # ドキュメント1
    (concepts_dir / "pid-control.md").write_text(
        """---
type: Concept
title: PID制御
description: 比例・積分・微分を用いたフィードバック制御
tags:
  - control
  - robotics
status: stable
---

# PID制御
PID制御は、[[フィードバック制御]] の基本アルゴリズムです。
""",
        encoding="utf-8",
    )

    # ドキュメント2 (リンク先)
    (concepts_dir / "feedback-control.md").write_text(
        """---
type: Concept
title: フィードバック制御
description: 出力を入力側にフィードバックして目標値に追従させる制御
tags:
  - control
status: stable
---

# フィードバック制御
出力をセンサーで計測し、目標値との偏差を修正します。
""",
        encoding="utf-8",
    )

    mock_llm = MagicMock()
    mock_llm.generate.return_value = "PID制御とフィードバック制御に関する統合回答です。"

    engine = LightweightGraphSearchEngine(llm_client=mock_llm)
    result = engine.search(query="PID制御 フィードバック", wiki_dir=wiki_dir, top_k=2)

    assert len(result.main_hits) >= 1
    assert result.main_hits[0]["title"] == "PID制御" or result.main_hits[0]["title"] == "フィードバック制御"
    # 1-Hop でフィードバック制御が巡回抽出されているか
    traversed_terms = [t["term"] for t in result.traversed_glossary_terms]
    assert "フィードバック制御" in traversed_terms or any("フィードバック制御" in h["title"] for h in result.main_hits)
    assert result.integrated_answer == "PID制御とフィードバック制御に関する統合回答です。"

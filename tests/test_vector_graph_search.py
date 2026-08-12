from pathlib import Path
import pytest
from wikid_steward.vector.indexer import QdrantKnowledgeIndexer
from wikid_steward.vector.searcher import WikiGraphSearchEngine


def test_qdrant_indexer_and_graph_search(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    glossary_dir = wiki_dir / "glossary"
    llm_dir = wiki_dir / "llm"
    glossary_dir.mkdir(parents=True)
    llm_dir.mkdir(parents=True)

    # 1. 用語ノート作成
    (glossary_dir / "llm-as-a-judge.md").write_text(
        "---\ntitle: LLM-as-a-judge\ntype: Glossary Term\n---\n# LLM-as-a-judge\n\n大規模言語モデルを評価者として用いる評価パラダイム。",
        encoding="utf-8",
    )

    # 2. メイン文書ノート作成
    (llm_dir / "paper_eval.md").write_text(
        "---\ntitle: LLM Evaluation Survey\ntype: Academic Paper\n---\n# LLM Evaluation\n\nWe present a survey on [[LLM-as-a-judge]] techniques for automated model scoring.",
        encoding="utf-8",
    )

    # 3. インデクサーの実行 (インメモリ)
    indexer = QdrantKnowledgeIndexer(location=":memory:")
    indexed_count = indexer.index_wiki_directory(wiki_dir)
    assert indexed_count > 0

    # 4. グラフ拡張検索の実行
    search_engine = WikiGraphSearchEngine(indexer=indexer)
    result = search_engine.search(
        query="What is LLM-as-a-judge evaluation?", wiki_dir=wiki_dir, top_k=2
    )

    # アサート検証
    assert result.query == "What is LLM-as-a-judge evaluation?"
    assert len(result.main_hits) > 0
    # 1-Hop グラフ巡回で用語 [[LLM-as-a-judge]] が自律抽出されていること
    assert len(result.traversed_glossary_terms) > 0
    assert result.traversed_glossary_terms[0]["term"] == "LLM-as-a-judge"
    assert "LLM-as-a-judge" in result.integrated_answer or "評価" in result.integrated_answer

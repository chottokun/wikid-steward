from pathlib import Path

from wikid_steward.core.llm_client import OpenAICompatibleLLMClient
from wikid_steward.vector.indexer import (
    OpenAICompatibleEmbeddingClient,
    QdrantKnowledgeIndexer,
)
from wikid_steward.vector.searcher import WikiGraphSearchEngine


class MockEmbeddingClient(OpenAICompatibleEmbeddingClient):
    def __init__(self):
        self.base_url = "http://mock-embedding"
        self.model = "mock-model"

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]


class MockLLMClient(OpenAICompatibleLLMClient):
    def __init__(self):
        pass

    def generate_chat_completion(
        self, messages: list[dict], system_prompt: str | None = None
    ) -> str:
        return "ハブノードテスト用の統合回答。"


def test_hub_node_degree_cutoff_and_token_budgeting(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    glossary_dir = wiki_dir / "glossary"
    docs_dir = wiki_dir / "docs"
    glossary_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)

    # 1. 巨大ハブ用語 [[AI]] の作成
    (glossary_dir / "ai.md").write_text(
        "---\ntitle: AI\ntype: Glossary Term\n---\n# AI\n\n人工知能に関する汎用概念説明。" * 50,
        encoding="utf-8",
    )

    # 2. 30 個のダミーノートを作成し [[AI]] を大量バックリンク参照させる（度数 30 > 閾値 25）
    for i in range(30):
        (docs_dir / f"doc_{i}.md").write_text(
            f"---\ntitle: Doc {i}\ntype: Paper\n---\n# Doc {i}\n\nThis paper discusses [[AI]] and [[Machine Learning]] applications in industry.",
            encoding="utf-8",
        )

    # 3. インデクサーと検索エンジンの初期化
    mock_embed = MockEmbeddingClient()
    mock_llm = MockLLMClient()
    indexer = QdrantKnowledgeIndexer(location=":memory:", embedding_client=mock_embed)
    indexer.index_wiki_directory(wiki_dir)

    search_engine = WikiGraphSearchEngine(indexer=indexer, llm_client=mock_llm)

    # 4. 巨大ハブノードテストの実行
    result = search_engine.search(
        query="Explain AI and Machine Learning", wiki_dir=wiki_dir, top_k=3
    )

    # 検証 ①: 度数閾値 (max_hub_degree=25) により [[AI]] がハブノードとして簡易参照化されていること
    hub_terms = [g for g in result.traversed_glossary_terms if g.get("is_hub")]
    assert len(hub_terms) > 0, "FAILED: Hub node was not detected!"
    assert any(g["term"].upper() == "AI" for g in hub_terms), (
        "FAILED: AI was not detected as a hub term!"
    )
    assert "巨大ハブノード" in hub_terms[0]["content"]

    # 検証 ②: トークンオーバーフロー防止 (全体テキスト長が 4000 トークン相当以内に収まっていること)
    total_context_length = sum(len(hit.get("content", "")) for hit in result.main_hits) + sum(
        len(g.get("content", "")) for g in result.traversed_glossary_terms
    )
    assert total_context_length < 12000, "FAILED: Context exceeded max token budget limit!"

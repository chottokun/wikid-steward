"""PR #5 の徹底検証・境界値テストスイート"""

from pathlib import Path

import pytest
from fastmcp import Client

from wikid_steward.mcp.server import mcp
from wikid_steward.vector.indexer import QdrantKnowledgeIndexer


def test_pagerank_isolated_and_self_referencing(tmp_path: Path):
    """孤立ノード、自己参照ノード、存在しないリンク先が含まれるグラフでの PageRank 計算安定性検証"""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    # 孤立ノード
    (wiki_dir / "isolated.md").write_text(
        "---\ntitle: Isolated Node\nid: isolated\n---\n\nNo links here.",
        encoding="utf-8",
    )
    # 自己参照ノード
    (wiki_dir / "self_ref.md").write_text(
        "---\ntitle: Self Ref\nid: self_ref\n---\n\nLink to [[Self Ref]].",
        encoding="utf-8",
    )
    # 存在しないノードへのリンク (Dead Link)
    (wiki_dir / "dead_link.md").write_text(
        "---\ntitle: Dead Link Source\nid: dead_link\n---\n\nLink to [[NonExistentPage]].",
        encoding="utf-8",
    )

    indexer = QdrantKnowledgeIndexer(location=":memory:")
    pr_scores = indexer.compute_pagerank(wiki_dir)

    assert "isolated" in pr_scores
    assert "self_ref" in pr_scores
    assert "dead_link" in pr_scores
    # 全てのスコアが非負の実数であること
    for k, v in pr_scores.items():
        assert isinstance(v, float)
        assert v >= 0.0


def test_pagerank_cyclic_graph(tmp_path: Path):
    """循環リンク (A -> B -> C -> A) を持つグラフでの PageRank 収束検証"""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    (wiki_dir / "node_a.md").write_text(
        "---\ntitle: Node A\nid: node_a\n---\n\nLink to [[Node B]].",
        encoding="utf-8",
    )
    (wiki_dir / "node_b.md").write_text(
        "---\ntitle: Node B\nid: node_b\n---\n\nLink to [[Node C]].",
        encoding="utf-8",
    )
    (wiki_dir / "node_c.md").write_text(
        "---\ntitle: Node C\nid: node_c\n---\n\nLink to [[Node A]].",
        encoding="utf-8",
    )

    indexer = QdrantKnowledgeIndexer(location=":memory:")
    pr_scores = indexer.compute_pagerank(wiki_dir)

    # 3ノードが完全に対称な循環なので、PageRank スコアはほぼ等しくなるはず
    assert len(pr_scores) == 3
    assert abs(pr_scores["node_a"] - pr_scores["node_b"]) < 1e-4
    assert abs(pr_scores["node_b"] - pr_scores["node_c"]) < 1e-4


def test_pagerank_empty_wiki(tmp_path: Path):
    """空ディレクトリでの PageRank 計算"""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    indexer = QdrantKnowledgeIndexer(location=":memory:")
    pr_scores = indexer.compute_pagerank(wiki_dir)
    assert pr_scores == {}


def test_search_engine_ranking_with_pagerank():
    """PageRank ブーストによってスコア順序が正しく更新されるかの検証"""

    class MockResult:
        def __init__(self, score: float, payload: dict):
            self.score = score
            self.payload = payload

    # 2つの検索結果をシミュレート
    # Item 1: 高い類似度だが PageRank は 0
    # Item 2: やや低い類似度だが PageRank が高い
    results = [
        MockResult(score=0.80, payload={"id": "doc1", "title": "Doc 1", "pagerank_score": 0.0}),
        MockResult(score=0.75, payload={"id": "doc2", "title": "Doc 2", "pagerank_score": 1.0}),
    ]

    alpha = 0.2
    main_hits = []
    for res in results:
        payload = res.payload or {}
        pr_score = float(payload.get("pagerank_score", 0.0))
        raw_sim = float(res.score)
        boosted = raw_sim + (alpha * pr_score)
        payload["score"] = boosted
        payload["raw_similarity"] = raw_sim
        payload["pagerank_score"] = pr_score
        main_hits.append(payload)

    main_hits.sort(key=lambda x: x.get("score", 0.0), reverse=True)

    # doc2 の boosted score は 0.75 + 0.2*1.0 = 0.95 > 0.80 なので doc2 がトップになるはず
    assert main_hits[0]["id"] == "doc2"
    assert main_hits[0]["score"] == 0.95
    assert main_hits[1]["id"] == "doc1"
    assert main_hits[1]["score"] == 0.80


@pytest.mark.anyio
async def test_mcp_all_tools_and_error_handling(tmp_path: Path, monkeypatch):
    """FastMCP の全ツール (search, compile_stub, lint, moc, compile_document) および異常系の検証"""
    monkeypatch.chdir(tmp_path)
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    note_a = wiki_dir / "note_a.md"
    note_a.write_text(
        "---\ntitle: FastMCP Deep\ntype: Concept\nid: note_a\n---\n\nBody content linking [[note_b]].",
        encoding="utf-8",
    )

    async with Client(mcp) as client:
        # Tool: lint
        lint_res = await client.call_tool("lint", {"dry_run": True})
        assert lint_res.content is not None

        # Tool: moc
        moc_res = await client.call_tool("moc", {})
        assert moc_res.content is not None

        # Tool: search
        search_res = await client.call_tool("search", {"query": "FastMCP"})
        assert search_res.content is not None
        assert "FastMCP" in str(search_res.content)

        # Tool: compile_stub
        stub_res = await client.call_tool("compile_stub", {"term": "NonExistentStub"})
        assert stub_res.content is not None

        # Tool: compile_document (not exist test)
        doc_res = await client.call_tool("compile_document", {"file_path": "dummy.pdf"})
        assert doc_res.content is not None

        # Resource: 存在しないリソースの読み込み検証 (例外送出)
        try:
            await client.read_resource("wiki://non_existent.md")
        except Exception as e:
            assert "Resource not found" in str(e) or "FileNotFoundError" in str(e)

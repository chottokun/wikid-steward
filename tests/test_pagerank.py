from pathlib import Path

from wikid_steward.vector.indexer import QdrantKnowledgeIndexer


def test_pagerank_computation(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    node_a = wiki_dir / "note_a.md"
    node_b = wiki_dir / "note_b.md"
    node_c = wiki_dir / "note_c.md"

    # A -> B, C -> B (B is heavily referenced)
    node_a.write_text(
        "---\ntitle: Note A\nid: note_a\n---\n\nLink to [[Note B]].", encoding="utf-8"
    )
    node_b.write_text("---\ntitle: Note B\nid: note_b\n---\n\nContent of B.", encoding="utf-8")
    node_c.write_text(
        "---\ntitle: Note C\nid: note_c\n---\n\nLink to [[Note B]].", encoding="utf-8"
    )

    indexer = QdrantKnowledgeIndexer(location=":memory:")
    pr_scores = indexer.compute_pagerank(wiki_dir)

    assert "note_b" in pr_scores
    assert "note_a" in pr_scores
    assert "note_c" in pr_scores
    assert pr_scores["note_b"] > pr_scores["note_a"]
    assert pr_scores["note_b"] > pr_scores["note_c"]


def test_indexing_with_pagerank_payload(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    doc = wiki_dir / "doc.md"
    doc.write_text(
        "---\ntitle: Doc\nid: doc\ntype: Concept\n---\n\nDoc body paragraph.", encoding="utf-8"
    )

    indexer = QdrantKnowledgeIndexer(location=":memory:")
    indexed_count = indexer.index_wiki_directory(wiki_dir)
    assert indexed_count > 0

    points, _ = indexer.client.scroll(collection_name=indexer.collection_name, limit=10)
    assert len(points) > 0
    payload = points[0].payload
    assert "pagerank_score" in payload
    assert isinstance(payload["pagerank_score"], float)

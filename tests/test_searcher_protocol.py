from pathlib import Path

from wikid_steward.core.graph_searcher import LightweightGraphSearchEngine
from wikid_steward.vector.searcher import (
    FallbackSearchEngine,
    SearcherProtocol,
    WikiGraphSearchEngine,
    create_search_engine,
)


def test_searcher_protocol_conformance():
    lightweight_engine = LightweightGraphSearchEngine()
    qdrant_engine = WikiGraphSearchEngine(indexer=None)
    fallback_engine = FallbackSearchEngine(
        primary_engine=qdrant_engine, fallback_engine=lightweight_engine
    )

    assert isinstance(lightweight_engine, SearcherProtocol)
    assert isinstance(qdrant_engine, SearcherProtocol)
    assert isinstance(fallback_engine, SearcherProtocol)


def test_create_search_engine_backends():
    e_light = create_search_engine(backend="lightweight")
    assert isinstance(e_light, LightweightGraphSearchEngine)

    e_auto = create_search_engine(backend="auto")
    assert isinstance(e_auto, SearcherProtocol)


def test_fallback_search_execution(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    doc_file = wiki_dir / "sample.md"
    doc_file.write_text(
        "---\ntitle: Sample Note\ntype: Concept\n---\n\nSample content about [[PID Control]].",
        encoding="utf-8",
    )

    class FailingPrimaryEngine:
        def search(
            self, query: str, wiki_dir: Path | str, top_k: int = 3, max_traversal_depth: int = 1
        ):
            raise RuntimeError("Primary Qdrant engine simulated failure")

    lightweight_engine = LightweightGraphSearchEngine()
    fallback_engine = FallbackSearchEngine(
        primary_engine=FailingPrimaryEngine(),
        fallback_engine=lightweight_engine,
    )

    res = fallback_engine.search(query="Sample", wiki_dir=wiki_dir, top_k=3)
    assert res is not None
    assert len(res.main_hits) > 0
    assert res.main_hits[0]["title"] == "Sample Note"

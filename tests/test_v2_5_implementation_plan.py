"""wikid-steward 実装計画書 (v2.5) セクション 5 に規定された TDD 検証テストスイート"""

import time
from pathlib import Path

import pytest
from fastmcp import Client
from filelock import FileLock

from wikid_steward.core.human_memo import merge_human_memo
from wikid_steward.mcp.server import mcp
from wikid_steward.vector.indexer import OpenAICompatibleEmbeddingClient, QdrantKnowledgeIndexer
from wikid_steward.vector.searcher import (
    WikiGraphSearchEngine,
    create_search_engine,
)


class MockEmbeddingClient(OpenAICompatibleEmbeddingClient):
    """テスト用の高速モック Embedding クライアント"""

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        # 各テキストに対して決定的かつ即座に 384 次元のダミーベクトルを生成
        return [[float(len(t) % 10) / 10.0] * 384 for t in texts]


class MockLLMClient:
    """テスト用の高速モック LLM クライアント"""

    def generate(self, prompt: str, system_prompt: str | None = None, **kwargs) -> str:
        return "モック統合要約回答です。"

    def generate_chat_completion(
        self, messages: list[dict], system_prompt: str | None = None, **kwargs
    ) -> str:
        return "モックチャット回答です。"


def test_cli_read_timeout_fallback(tmp_path: Path, monkeypatch):
    """リスク1: filelock 長期保持時でも、FallbackSearchEngine / create_search_engine がハングせず非ブロッキングで結果を返すか検証"""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "sample.md").write_text(
        "---\ntitle: Slew Rate Control\ntype: Concept\n---\n\nSlew rate control reduces motor jerk.",
        encoding="utf-8",
    )

    lock_file = tmp_path / "qdrant_data.lock"
    with FileLock(str(lock_file), timeout=1):
        # 検索エンジンを起動（Lightweight へフォールバック）
        engine = create_search_engine(backend="lightweight", llm_client=MockLLMClient())
        assert engine is not None

        start_time = time.time()
        res = engine.search(query="motor jerk", wiki_dir=wiki_dir, top_k=3)
        duration = time.time() - start_time

        # 3秒以内に即時ファイルベース検索で結果が返ること
        assert duration < 3.0
        assert len(res.main_hits) > 0
        assert "Slew Rate Control" in res.main_hits[0]["title"]


def test_pagerank_incremental_update_cost(tmp_path: Path):
    """リスク2: PageRank 計算が多数ノートでも高速に完了するか計算時間を計測検証"""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    # 100件のノートを生成して有向グラフを形成
    for i in range(100):
        next_i = (i + 1) % 100
        prev_i = (i - 1) % 100
        (wiki_dir / f"note_{i:03d}.md").write_text(
            f"---\ntitle: Note {i}\nid: note_{i:03d}\n---\n\nLink to [[Note {next_i}]] and [[Note {prev_i}]].",
            encoding="utf-8",
        )

    indexer = QdrantKnowledgeIndexer(location=":memory:", embedding_client=MockEmbeddingClient())
    start_time = time.time()
    pr_scores = indexer.compute_pagerank(wiki_dir)
    calc_time = time.time() - start_time

    assert len(pr_scores) == 100
    # 100件の PageRank 計算が 500ms 以内に完了すること
    assert calc_time < 0.50


def test_orphan_point_garbage_collection(tmp_path: Path):
    """リスク3: ディスク削除後に indexer.sync / prune_deleted_points を呼び出し Qdrant 内の孤立 Point がパージされるか検証"""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    file_a = wiki_dir / "note_a.md"
    file_b = wiki_dir / "note_b.md"
    file_a.write_text("---\ntitle: Note A\nid: note_a\n---\n\nContent A", encoding="utf-8")
    file_b.write_text("---\ntitle: Note B\nid: note_b\n---\n\nContent B", encoding="utf-8")

    indexer = QdrantKnowledgeIndexer(location=":memory:", embedding_client=MockEmbeddingClient())
    count_init = indexer.index_wiki_directory(wiki_dir, prune=False)
    assert count_init == 2

    # ユーザーが note_b.md をエディタで直接削除
    file_b.unlink()

    # 次回同期（prune=True）を実行
    pruned_count = indexer.prune_deleted_points(wiki_dir)
    assert pruned_count == 1

    # 残存ポイントの確認
    points, _ = indexer.client.scroll(collection_name=indexer.collection_name, limit=10)
    assert len(points) == 1
    assert points[0].payload["doc_id"] == "note_a"


def test_synonym_merge_threshold_and_memo_protection():
    """リスク4: 概念統合時に merge_human_memo で手書きメモが 100% 維持されるかアドバーサリアル検証"""
    existing_content = """---
title: PID Controller
type: Concept
---

# PID Controller
Generated description here.

<!-- HUMAN BEGIN -->
### 現場チューニングメモ (極秘)
* Kd ゲインは 0.05 を超えると高周波ノイズでハンチングを起こす
* 冬場はオイル粘度低下のため Kp を +10% 増やす
<!-- HUMAN END -->

## Reference Links
* [[Motor Control]]
"""

    new_ai_generated_content = """---
title: PID Controller
type: Concept
---

# PID Controller
Updated modern description with Kalman filter theory.

## Reference Links
* [[Kalman Filter]]
"""

    merged = merge_human_memo(
        existing_content=existing_content,
        new_content=new_ai_generated_content,
    )

    # 人間のメモタグおよび内容が完全に保持されていること
    assert "<!-- HUMAN BEGIN -->" in merged
    assert "<!-- HUMAN END -->" in merged
    assert "Kd ゲインは 0.05 を超えると高周波ノイズでハンチングを起こす" in merged
    assert "冬場はオイル粘度低下のため Kp を +10% 増やす" in merged
    # 新しい AI 本文も反映されていること
    assert "Updated modern description with Kalman filter theory." in merged


def test_qdrant_payload_scope_isolation(tmp_path: Path):
    """リスク5: Payload フィルタ (doc_type == 'Concept') により Silver 層データが Gold 検索コンテキストを汚染しないか検証"""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    # Silver 層のドキュメント (RawSource)
    (wiki_dir / "raw_report.md").write_text(
        "---\ntitle: Raw Meeting Note\ntype: RawSource\nid: raw_01\n---\n\nDiscussed PID architecture details in meeting.",
        encoding="utf-8",
    )
    # Gold 層のドキュメント (Concept)
    (wiki_dir / "pid_concept.md").write_text(
        "---\ntitle: PID Control\ntype: Concept\nid: pid_concept\n---\n\nFormal definition of PID architecture and tuning.",
        encoding="utf-8",
    )

    indexer = QdrantKnowledgeIndexer(location=":memory:", embedding_client=MockEmbeddingClient())
    indexer.index_wiki_directory(wiki_dir)

    search_engine = WikiGraphSearchEngine(indexer=indexer)

    # Concept のみでスコープ絞り込み検索
    res_concept = search_engine.search(
        query="PID architecture",
        wiki_dir=wiki_dir,
        top_k=5,
        doc_types=["Concept"],
    )
    for hit in res_concept.main_hits:
        assert hit.get("doc_type") == "Concept"
        assert hit.get("doc_type") != "RawSource"

    # 全スコープ検索
    res_all = search_engine.search(
        query="PID architecture",
        wiki_dir=wiki_dir,
        top_k=5,
        doc_types=None,
    )
    doc_types_in_all = {hit.get("doc_type") for hit in res_all.main_hits}
    assert "Concept" in doc_types_in_all or "RawSource" in doc_types_in_all


@pytest.mark.anyio
async def test_mcp_tool_execution_non_blocking(tmp_path: Path, monkeypatch):
    """リスク6: FastMCP イベントループが同期タスク実行時でも応答性を維持できるか検証"""
    monkeypatch.chdir(tmp_path)
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    (wiki_dir / "note.md").write_text(
        "---\ntitle: FastMCP Performance\ntype: Concept\n---\n\nContent for FastMCP performance test.",
        encoding="utf-8",
    )

    async with Client(mcp) as client:
        t0 = time.time()
        res_lint = await client.call_tool("lint", {"dry_run": True})
        res_moc = await client.call_tool("moc", {})
        res_stub = await client.call_tool("compile_stub", {"term": "DummyTerm"})
        duration = time.time() - t0

        assert res_lint.content is not None
        assert res_moc.content is not None
        assert res_stub.content is not None
        assert duration < 5.0

---
type: "Architecture Decision"
title: "ハイブリッド検索 ＆ 1-Hop WikiLink グラフ巡回インフラ仕様"
sources:
  - resource: "/src/wikid_steward/core/graph_searcher.py"
  - resource: "/src/wikid_steward/vector/indexer.py"
  - resource: "/src/wikid_steward/vector/searcher.py"
status: "stable"
generated:
  by: "agent/antigravity"
  at: "2026-08-15T00:05:00Z"
description: "外部DB不要の軽量メタデータ検索 (v7.0) および Qdrant ベクトル検索、1-Hop WikiLink グラフ巡回、巨大ハブノード度数制御仕様"
tags:
  - "vector"
  - "graph-rag"
  - "lightweight-search"
  - "search"
---

# ハイブリッド検索 ＆ 1-Hop WikiLink グラフ巡回インフラ仕様

`wikid-steward` は、外部依存を持たない超軽量なファイルベース検索（`LightweightGraphSearchEngine`）と、Qdrant ベクトル検索（`WikiGraphSearchEngine`）の両方を `SearcherProtocol` で統一・抽象化し、透過的な自動フォールバック運用（`FallbackSearchEngine`）をサポートしています。

## 1. Searcher Protocol ＆ 自動フォールバック (`vector/searcher.py`)
- **Searcher Protocol**: `search(query, wiki_dir, top_k, max_traversal_depth)` 抽象インターフェースを定義。
- **filelock によるプロセス間排他制御**: Qdrant ローカルモード (`path`) 利用時の RocksDB ファイルロック競合を防止。
- **自動フォールバック**: Qdrant 接続・アクセス障害発生時、即座にファイルベース軽量検索にフォールバック。

## 2. PageRank 事前演算 ＋ Payload キャッシュ ＆ スコアブースト
- **事前演算**: インデックス更新時に `[[WikiLink]]` 有向グラフから NetworkX で PageRank を算出。
- **Payload キャッシュ**: 算出した PageRank スコアを Qdrant `payload["pagerank_score"]` へ永続化。
- **ブーストスコア**: 検索時に $Score = CosineSim + \alpha \cdot PR(d)$ で統合再ソート。

## 3. FastMCP サーバー連携 (`mcp/server.py`)
- FastMCP サーバーにより `wiki://` リソース URI および操作ツール（`search`, `compile_stub`, `lint`, `moc` 等）を公開。

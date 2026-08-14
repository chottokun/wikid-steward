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

`wikid-steward` は、外部依存を持たない超軽量なファイルベース検索（v7.0 標準）と、大規模コーパス向けの Qdrant ベクトル検索の両方を柔軟にサポートしています。

## 1. 超軽量ファイルベース 1-Hop グラフ検索 (`core/graph_searcher.py`) [v7.0 標準]
- **外部 DB 不要**: Qdrant 等のサーバー構築なしで、純粋な Python スクリプトのみで実行可能。
- **OKF 構造化メタデータスコアリング**: `title`, `tags`, `description`, `aliases` の前方一致・スコアリングでメイン該当ノートを選定。
- **1-Hop 接続グラフ巡回**: メイン該当ノートの `[[WikiLink]]` やバックリンク（前提定義）を自動探索し、LLM が統合レポート回答を生成。

## 2. Qdrant ベクトル検索 ＆ 1-Hop グラフ巡回 (`vector/searcher.py`)
- **ベクトル検索**: OpenAI 互換 Embedding でテキストブロックを多次元ベクトル化し、Qdrant から類似度の高い Top-K チャンクを抽出。
- **巨大ハブノード度数制御 (Degree Cutoff)**: ナレッジ全体での言及回数（Degree）が `max_hub_degree` を超える用語は簡易参照に縮約。
- **トークンバジェット制御 (Token Budget Control)**: 累積トークン数が `max_traversal_tokens` に達した時点で巡回を自動打ち切り。
- **LLM 統合回答生成**: メイン検索ヒット情報と 1-Hop 巡回で得られた専門用語定義を合成し、網羅的なレポートを出力。

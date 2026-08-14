---
type: "Architecture Decision"
title: "軽量メタデータ ＆ 1-Hop グラフ巡回検索仕様 (v7.0)"
sources:
  - resource: "/src/wikid_steward/core/graph_searcher.py"
status: "stable"
generated:
  by: "agent/antigravity"
  at: "2026-08-15T00:05:00Z"
description: "外部ベクトルDBに依存しない、OKFメタデータと1-Hop WikiLinkグラフ巡回による超軽量検索エンジンの仕様"
tags:
  - "graph-search"
  - "metadata"
  - "1-hop"
  - "lightweight"
---

# 軽量メタデータ ＆ 1-Hop グラフ巡回検索仕様 (`core/graph_searcher.py`)

外部の重厚なベクトル DB（Qdrant / Milvus 等）に依存せず、純粋な Python スクリプトと OKF v0.2 メタデータ、および `[[WikiLink]]` 接続グラフのみで高速かつ文脈豊かな検索・要約レポートを提供するエンジン。

## 検索・回答合成の仕組み

```mermaid
flowchart LR
    A["クエリ入力"] --> B["1. メタデータ & 全文スコアリング"]
    B --> C["2. メイン該当ノート特定 (Top-K)"]
    C --> D["3. 1-Hop [[WikiLink]] 巡回 (関連定義・前提知識抽出)"]
    D --> E["4. LLM 統合要約回答レポート生成"]
```

1. **メタデータ ＆ 全文スコアリング**:
   - OKF フロントマター（`title`, `description`, `tags`, `aliases`）および本文のキーワードマッチングにより、メイン該当ノートをスコアリング・選定。
2. **1-Hop グラフ巡回**:
   - メインノートに含まれる `[[WikiLink]]` およびバックリンク（被リンク元）を 1-Hop 探索し、前提定義ノートの概要スニペットを収集。
   - ハブ度数制限（上限ノード数）により、無駄なコンテキスト爆発を抑制。
3. **LLM 統合要約回答**:
   - 抽出されたメインノート本文と関連用語定義をプロンプトに統合し、LLM が前提知識を整理した日本語の要約回答レポートを出力。

## 実行インターフェース

```bash
uv run wikid-steward search "PID制御とフィードバック"
```

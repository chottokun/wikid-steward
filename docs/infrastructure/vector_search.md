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
  at: "2026-08-19T21:42:00Z"
description: "外部DB不要の軽量ファイルベース検索および Qdrant ベクトル検索、PageRank 事前計算、ガベージコレクション、1-Hop WikiLink グラフ巡回の詳細仕様と運用ガイド"
tags:
  - "vector"
  - "graph-rag"
  - "pagerank"
  - "lightweight-search"
  - "garbage-collection"
  - "qdrant"
---

# ハイブリッド検索 ＆ 1-Hop WikiLink グラフ巡回インフラ仕様

`wikid-steward` は、外部依存を持たない超軽量なファイルベース検索（`LightweightGraphSearchEngine`）と、高次元ベクトル検索（`WikiGraphSearchEngine`）の両方を `SearcherProtocol` で統一・抽象化し、透過的な自動フォールバック運用（`FallbackSearchEngine`）と高速 PageRank ブーストを提供します。

---

## 1. アーキテクチャ構成

```
                      ┌────────────────────────────────────────┐
                      │            SearcherProtocol            │
                      └───────────────────┬────────────────────┘
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   ▼                                             ▼
        [WikiGraphSearchEngine]                    [LightweightGraphSearchEngine]
   (Qdrant ベクトル + PageRank ブースト)             (ゼロ外部依存・純粋 Python 検索)
                   │                                             │
                   │ (障害 / ロック競合時に自動フォールバック)        │
                   └─────────────────────────────────────────────┘
```

---

## 2. コア機能の詳細仕様

### 2.1 Searcher Protocol と自動フォールバック
* **抽象プロトコル (`SearcherProtocol`)**:
  ```python
  def search(
      query: str,
      wiki_dir: Path | str,
      top_k: int = 3,
      max_traversal_depth: int = 1,
      doc_types: list[str] | None = None,
  ) -> SearchResult: ...
  ```
* **透過的フォールバック (`FallbackSearchEngine`)**:
  プライマリの Qdrant 検索エンジンで例外が発生した場合や、Qdrant が未起動・ロック競合を起こしている場合でも、自動的に `LightweightGraphSearchEngine` へ切り替わり、非ブロッキングで結果を返します。

### 2.2 PageRank 事前計算 ＋ Payload キャッシュ
毎回のクエリ時にグラフ再計算を行うオーバーヘッドを排除するため、インデックス同期時に NetworkX を用いて PageRank スコアを事前計算します：

1. **有向グラフ $G=(V, E)$ の構築**: 全 Markdown ファイルの Frontmatter メタデータおよび本文中の `[[WikiLink]]` を解析。
2. **PageRank 算出**: Power Iteration 法（ダンピング係数 $d = 0.85$）により各ドキュメントの PageRank $PR(d)$ を算出。
3. **Payload 永続化**: Qdrant の各チャンク Point の `payload["pagerank_score"]` に格納。
4. **$O(1)$ スコアブースト**:
   検索時はベクトル類似度 $Sim(q, d)$ とキャッシュされた PageRank を組み合わせ、以下の式で統合スコアを算出して再ソートします：
   $$Score_{final} = Sim(q, d) + \alpha \cdot PR(d) \quad (\alpha = 0.2)$$

### 2.3 プロセス間排他制御 (`filelock`)
* ローカル組み込みモード (`QdrantClient(path="./qdrant_data")`) では、RocksDB のプロセス多重オープンによる破損を防ぐため、`.lock` ファイルによる排他制御（タイムアウト: 10秒）を行います。
* バックグラウンドでインデックス書き込みが走っている最中に CLI 検索が実行された場合も、タイムアウト後に安全にファイルベース検索へフォールバックします。

### 2.4 孤立 Point の自律ガベージコレクション (GC)
* ユーザーが Obsidian や VSCode 等のエディタで Markdown ファイルを直接物理削除した場合、次回インデックス同期時（`wikid-steward index`）に Qdrant コレクション内をスクロール照合。
* ディスク上に存在しないファイルに対応する Point を検知し、`PointIdsList` によりコレクションから自動パージ（`prune_deleted_points`）します。

### 2.5 検索スコープ分離 (`doc_types`)
* `doc_types=["Concept"]` や `doc_types=["Concept", "Guide"]` を指定することで、Silver 層（`RawSource`: 生ドキュメント）による検索結果の重複・汚染を防ぎ、Gold 層の洗練された概念ノートのみを RAG コンテキストとして抽出できます。

---

## 3. Qdrant 接続モードの切り替え

`config.yaml` または環境変数で、ローカル組み込みモードとリモート Docker サーバーモードを切り替えることができます。

### ローカル埋め込みモード（デフォルト）
追加のサーバープロセスを起動せず、ローカルファイルにベクトルを永続化します。
```yaml
vector_db:
  url: "./qdrant_data"
  collection_name: "wikid_steward_knowledge"
  embedding_base_url: "http://localhost:11434/v1"
  embedding_model: "bge-small-en"
```

### Docker / サーバーモード（マルチプロセス・チーム共有）
```yaml
vector_db:
  url: "http://localhost:6333"
  api_key: ""
  collection_name: "wikid_steward_knowledge"
```

---

## 4. CLI 利用手順 ＆ コマンド例

### 4.1 ナレッジベースのインデックス作成 ＆ GC
```bash
# 全 Markdown ノートをインデックス化し、削除済みファイルの孤立 Point を自動パージ
uv run wikid-steward index

# 孤立 Point のパージを行わずに高速同期する場合
uv run wikid-steward index --no-prune
```

### 4.2 ナレッジグラフ検索
```bash
# 自動判定 (auto) - Qdrant ベクトル検索 ＋ PageRank ブースト ＋ 自動フォールバック
uv run wikid-steward search "モーター制御のフィードバック設計"

# 検索対象を Concept ノートのみに限定 (Silver/Gold スコープ分離)
uv run wikid-steward search "PID制御" -t Concept

# 外部依存ゼロの完全軽量ファイルベース検索を強制
uv run wikid-steward search "PID制御" --backend lightweight
```

---

## 5. Python API 呼び出し例

```python
from pathlib import Path
from wikid_steward.vector.indexer import QdrantKnowledgeIndexer
from wikid_steward.vector.searcher import create_search_engine

wiki_dir = Path("./wiki")

# 1. インデックス作成と GC
indexer = QdrantKnowledgeIndexer()
indexed_count = indexer.index_wiki_directory(wiki_dir=wiki_dir, prune=True)
print(f"Indexed {indexed_count} chunks with PageRank scores.")

# 2. 検索エンジンの生成と実行
engine = create_search_engine(backend="auto")
result = engine.search(
    query="PID制御のパラメータ調整",
    wiki_dir=wiki_dir,
    top_k=3,
    doc_types=["Concept"],
)

print(f"Top Hit: {result.main_hits[0]['title']} (Score: {result.main_hits[0]['score']:.2f})")
print(f"Integrated Answer:\n{result.integrated_answer}")
```

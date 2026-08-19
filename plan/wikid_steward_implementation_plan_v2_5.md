# **wikid-steward 実装計画書 (v2.5)**

---

## **1. 概要と開発コンテキスト分析**

本報告書は、GitHub 上で公開されているリポジトリ **`wikid-steward` (v7.0)** を対象に、その核心的設計思想（**人間中心のガードレール保護**、**ポータビリティ**、**1-Hop ナレッジグラフ巡回**）を維持・強化しつつ、現代的な LLM/RAG エコシステムに必要な要素を包括的に統合した最終実装計画書 (v2.5) である。

本エコシステムでは、ローカル環境で動作する SimpleWiki をパブリッシング層（表示・共有）とし、`wikid-steward` がデータ管理、パイプライン制御、構造化（Staging/Knowledge 化）、および高度なコンテキスト抽出を担当する。

### **v2.5 における核心的設計強化**
1. **メダリオン・アーキテクチャ ＋ Silver層止め (Early Stopping)**: 生データ (Bronze) からテキスト抽出・構造化された Staging (Silver: `wiki/raw_markdown/`) 段階での処理完了を第一級の運用モードとして受容し、LLM による Gold層 (`wiki/concepts/`) 抽出のオーバーヘッドを人間主導でコントロールする。
2. **オンデマンド / 夜間バッチ同期**: リアルタイム常時同期に伴う CPU/Disk I/O や `filelock` 競合、LLM トークンコストを回避するため、夜間バッチ (Cron) および明示的コマンド実行を標準運用として定義する。
3. **Qdrant 二段階スケール ＋ filelock ＋ Searcher Protocol**: `QdrantClient(path=...)` （ローカル埋め込みモード）と `url="http://localhost:6333"` （Docker / Cloud サーバーモード）を透過的に切り替えるファクトリを実装し、ローカルモードでは `filelock` による排他制御と、完全ファイルベース検索 (`core/graph_searcher.py`) への自動フォールバック機構を備える。
4. **PageRank 事前計算 ＋ Qdrant Payload キャッシュ**: 毎検索時のグラフ再計算遅延を排除するため、インデックス同期時に PageRank を事前計算し、`payload["pagerank_score"]` へ永続化して $O(1)$ スコアブーストを実現する。
5. **人間手書きメモの絶対保護 (Guarded Merge)**: LLM による概念ノート重複マージ時には `merge_human_memo` ロジックを確実に呼び出し、`<!-- HUMAN BEGIN -->` コメントタグ内の人間メモを 100% 維持する。
6. **ユーザー直接削除 (Human Pruning) と自律ガベージコレクション**: ユーザーがエディタ等で Markdown ファイルを物理削除した場合、次回バッチ同期時に Qdrant コレクションから孤立 Point を自動削除し、`wikid-steward lint --auto-stub` でリンク切れを修復する。

---

## **2. データパイプラインとメダリオン 3 層構造**

```
 [Bronze層: _raw/] ──(決定論的パース)──▶ [Silver層: wiki/raw_markdown/] ──▶ 【ユーザー閲覧・直接利用】
                                                  │
                                                  │ (明示的指示 OR バックリンク蓄積)
                                                  ▼
                                       [Gold層: wiki/concepts/]
```

### **2.1 パイプライン 3 層仕様**

- **Bronze 層（生データ領域: `_raw/`）**  
  PDF、DOCX、PPTX、XLSX、ソースコード等の非構造化原本バイナリおよび投入テキストが配置される領域。
- **Silver 層（Staging 領域: `wiki/raw_markdown/`）**  
  `_raw/` のデータを決定論的にパースし、必須 OKF v0.2 メタデータ（`type: RawSource`, `title`, `source_path` 等）を付与した標準 Markdown 領域。**多くのドキュメントはこの段階で処理を止め、そのままナレッジとして閲覧・利用してよい（Silver層での止め / Early Stopping）。**
- **Gold 層（Knowledge 領域: `wiki/concepts/`）**  
  LLM エージェント (`retro_compiler.py` / `promoter.py`) が Silver 層から重要な技術概念を要約抽出・昇華させた高品質ナレッジ領域。被リンク数（`min_backlinks >= 3`）や明示的コマンドで生成され、重複マージ時は既存ノートの `<!-- HUMAN BEGIN -->` ブロックを完全に保護する。

---

## **3. パッケージ構造とモジュール配置**

現行リポジトリの Python パッケージ構成 (`src/wikid_steward/`) と完全整合させたモジュール配置：

- **Linter・品質ゲート**: `src/wikid_steward/core/linter.py` (および `types_schema.py`)  
  OKF v0.2 適合性チェック、Pydantic スキーマ検証、およびリンク切れの自動スタブ起票 (`--auto-stub`) を担当。
- **Qdrant インデックス・検索ファクトリ**: `src/wikid_steward/vector/indexer.py` および `searcher.py`  
  `config.yaml` / `.env` の設定に応じて `QdrantClient` の `path` / `url` を切り替えるファクトリ、`filelock` 排他制御、および削除ファイルのガベージコレクション (`prune_deleted_points`) を担当。
- **ナレッジ昇華・概念抽出エージェント**: `src/wikid_steward/core/retro_compiler.py` および `promoter.py`  
  Silver 領域からの概念抽出、重複検知、および `merge_human_memo` による手書きメモ保護を伴うマージ処理。
- **フォールバック検索（完全ファイルベース）**: `src/wikid_steward/core/graph_searcher.py`  
  Qdrant が未導入・停止中の環境でも動作する軽量な 1-Hop ナレッジグラフ検索。
- **抽象検索インターフェース**: `Searcher Protocol`  
  Qdrant 検索とファイルベース検索を同一のインターフェースでカプセル化し、例外発生時に自動フォールバックする。
- **FastMCP インターフェース**: `src/wikid_steward/mcp/`  
  FastMCP を用いた MCP サーバーおよび `wiki://` リソース URI / ナレッジ操作ツールの提供。
- **CLI エントリーポイント**: `src/wikid_steward/cli.py`  
  `wikid-steward search`, `wikid-steward index`, `wikid-steward mcp`, `wikid-steward lint` 等の超軽量 CLI。

---

## **4. 検索・コンテキストアセンブリ ＆ 排他制御戦略**

### **4.1 プロセス間排他制御 (`filelock`) ＆ タイムアウトフォールバック**
- `QdrantClient(path="./qdrant_data")` 使用時の RocksDB ファイルロック競合を防ぐため、`filelock` モジュールによる排他制御を導入する。
- バックグラウンドで長時間の書き込みインデックス作成が走っている最中に CLI 検索コマンドが実行された場合、指定タイムアウト（例: 3.0秒）後に自動的にファイルベース検索 (`graph_searcher.py`) へフォールバックし、CLI がハングしない非ブロッキング構造を実現する。

### **4.2 PageRank 事前計算 ＋ Qdrant Payload キャッシュ**
毎検索時のグラフ再構築遅延を回避するため、インデックス同期時（`indexer.py` 実行時）に Wiki 内の `[[WikiLink]]` 有向グラフ $G=(V, E)$ から PageRank スコア $PR(A)$ を事前算出する：

$$PR(A) = \frac{1-d}{N} + d \sum_{T \in B_A} \frac{PR(T)}{L(T)}$$

（$d$: ダンピングファクター 0.85、$N$: 全ドキュメント数、$B_A$: ノート $A$ への被参照集合、$L(T)$: ノート $T$ の送出リンク数）

算出結果を Qdrant の `payload["pagerank_score"]` に格納しておく。検索時はベクトル類似度 $Sim(q, d)$ と組み合わせ、以下のように $O(1)$ の計算コストで最終ブーストスコアを算出する：

$$Score_{final} = \alpha \cdot Sim(q, d) + \beta \cdot PR(d)$$

---

## **5. 技術的課題・リスク ＆ TDD 検証テスト戦略**

実装中に想定される隠れたリスクと、それを事前に検証するための自動テスト設計：

| 領域 | 潜在的リスク | 失敗シナリオ | TDD 検証テスト案 |
| :--- | :--- | :--- | :--- |
| **排他制御** | `filelock` 長期保持による CLI フリーズ | デーモン同期中に CLI 検索を叩くとハングまたは例外終了する | `test_cli_read_timeout_fallback`: ロック保持中に CLI 検索を実行し、3秒以内にファイルベースへフォールバックして非ブロッキングで結果を返すか検証 |
| **同期性能** | PageRank 全件計算による I/O 圧迫 | 1ファイル保存のたびに全 Payload 更新が走り CPU/Disk I/O が高止まりする | `test_pagerank_incremental_update_cost`: 1000件のノート更新時の同期時間を計測し 500ms 以内に完了するか検証 |
| **状態剥離** | Disk と Qdrant の状態剥離 (State Drift) | 手動削除したファイルが検索ヒットし、1-Hop 巡回時に 404/エラーが発生する | `test_orphan_point_garbage_collection`: ディスク削除後に `indexer.sync()` を呼び出し Qdrant 内の孤立 Point がパージされるか検証 |
| **概念統合** | LLM 概念抽出の重複・同音異義語混同 | 表記揺れ概念の分裂や、異義語の誤統合によるナレッジ汚染 | `test_synonym_merge_threshold_and_memo_protection`: コサイン類似度閾値で重複検知し、`merge_human_memo` で手書きメモを守れるかアドバーサリアル検証 |
| **検索汚染** | Silver層 (Staging) による検索重複 | Qdrant 検索で RawSource と Concept ノートが二重ヒットする | `test_qdrant_payload_scope_isolation`: Payload フィルタ (`doc_type == "Concept"`) により Silver 層データが RAG コンテキストを汚染しないか検証 |
| **MCP 並行性** | FastMCP 同期 I/O ブロッキング | 重い処理で MCP イベントループがブロックされ LLM タイムアウトが発生 | `test_mcp_tool_execution_non_blocking`: 非同期 MCP ハンドラーから ThreadPool 経由でタスクを実行し応答性を維持できるか検証 |

---

## **6. フェーズ別実装ロードマップ**

### **フェーズ 1: Staging パイプライン、Qdrant ローカル埋め込み・排他制御・フォールバック基盤の確立（目安: 1〜2週間）**
1. **インジェストと Staging (`wiki/raw_markdown/`) 生成の自動化**: 生ソース (`_raw/`) からのテキスト抽出と OKF v0.2 メタデータ付与。
2. **Pydantic スキーマ厳格化と品質ゲート (`core/linter.py`)**: `types_schema.py` の定義と Pydantic バリデーション。
3. **Qdrant クライアントファクトリ ＆ `filelock` 排他制御 (`vector/indexer.py`, `searcher.py`)**: `path` / `url` 切替ファクトリとタイムアウト付き `filelock` の実装。
4. **Searcher Protocol ＆ フォールバックの実装**: Qdrant 障害・ロック時に `core/graph_searcher.py` へ自動フォールバックする仕組み。
5. **ユーザー物理削除対応 (GC)**: 削除された Markdown ファイルの Qdrant からの自動パージ機構。

### **フェーズ 2: LLM ナレッジ昇華・PageRank キャッシュ・オンデマンド同期（目安: 2〜4週間）**
1. **概念抽出エージェント (`retro_compiler.py` / `promoter.py`)**: 重複検知と `merge_human_memo` による手書きメモ保護付き昇華処理。
2. **PageRank 事前計算 ＆ Payload キャッシュ**: インデックス作成時の PageRank 事前計算と `payload["pagerank_score"]` 保存。
3. **先進的コンテキストアセンブラ**: Payload フィルタ ＋ PageRank ブースト ＋ 1-Hop/2-Hop `[[WikiLink]]` グラフ展開モジュール。
4. **オンデマンド / バッチ同期切り替え**: 夜間バッチ (Cron) および手動コマンド実行 (`wikid-steward index`) モードの構築。

### **フェーズ 3: ネイティブ FastMCP サーバー化・自律クレンジング・スケール拡張（目安: 1ヶ月〜）**
1. **FastMCP サーバーの実装 (`src/wikid_steward/mcp/`)**: FastMCP による `wiki://` リソース URI および検索・コンパイルツールの公開。
2. **自律クレンジングデーモン**: `watchdog` と `linter.py (--auto-stub)` を統合したリンク切れ修復デーモンの稼働。
3. **Qdrant サーバーモード (Docker / Cloud) ドキュメント整備**: マルチプロセス/大規模環境向け Docker サーバー移行設定。

---

## **7. 結論**

本実装計画書 (v2.5) は、`wikid-steward` の核心価値である「ポータビリティ」と「人間中心の保護機構」を第一に尊重しつつ、運用上のリアリティ（**Silver層での止め**、**オンデマンド/夜間バッチ同期**、**ユーザーによる直接ファイル削除の許容**）を完璧に設計へ落とし込んだ最終計画である。

この計画に基づいて TDD 方式で検証テストを先行構築しながら実装を進めることで、ローカルからクラウドまでシームレスにスケールし、極めて信頼性の高い次世代ナレッジ管理エンジンが完成する。

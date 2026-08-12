# LLM-Wiki Phase 3 実装計画書: 用語自動抽出・WikiLink 相互リンク・グラフ拡張検索・動的 MOC システム

> **文書バージョン**: 1.0.0  
> **作成日**: 2026-08-12  
> **対象**: `wikid-steward` コア開発チーム  
> **目的**: Andrej Karpathy 氏の LLM Wiki 思想の核である「網の目のように相互接続された知識ネットワーク」を実現し、用語の自動抽出、WikiLink 自動形成、グラフ拡張検索 (Graph-Augmented Search)、動的 MOC (Map of Content) 生成、および OKF リントシステムを完全実装するための技術仕様と開発ロードマップを定義する。

---

## 1. 全体アーキテクチャ ＆ 処理フロー

本フェーズでは、パースされたドキュメントとアセット（テキスト、VLM 画像日本語要約、HTML `<table>`）に対し、**用語抽出・相互リンク・グラフ検索・MOC自動生成**を統合した高度な知識ネットワークを構築します。

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                   LLM-Wiki Phase 3 全体データフロー                      │
└──────────────────────────────────────────────────────────────────────────┘

 [ 原本ドキュメント ] ──> [ Docling & VLM パース ]
                                 │
                                 ▼
                     [ staging/ レビュー ＆ 昇格 ]
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       【Task 3-0: 用語抽出】          【Task 3-0: WikiLink 形成】
       (重要用語・概念の抽出)          (本文内の単語を [[用語]] 化)
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
                     [ wiki/ 相互接続 Vault ]
                                 │
                 ┌───────────────┼───────────────┐
                 ▼                               ▼
       【Task 3-1: グラフ拡張検索】     【Task 3-2: 動的 MOC & リント】
       (WikiLink 巡回 × ベクトル)       (カテゴリ別目次 ＆ 健全性検証)
```

---

## 2. タスク別詳細技術仕様

### 【Task 3-0】 用語自動抽出 (`glossary.py`) ＆ WikiLink 相互リンク形成 (`relinker.py`)

#### 概要
ドキュメントからドメイン専門用語やコア概念を抽出し、用語説明ノート (`wiki/glossary/{slug}.md`) を自動生成するとともに、ナレッジベース内の全ノート本文中の該当用語を自動的に **`[[用語名]]`** (Obsidian / WikiLink 形式) へ相互リンク接続します。

#### 詳細仕様
1. **用語自動抽出 (`src/wikid_steward/core/glossary.py`)**:
   * LLM / NER (Named Entity Recognition) またはパターン抽出を用いて、本文からドメインキーコンセプト（例: `LLM-as-a-judge`, `Continuous Latent Space`, `SBOM`）を抽出。
   * 用語説明ノートを OKF ヘッダー（`type: Glossary Term`）付きで `wiki/glossary/` 配下に自動作成。
2. **自動 WikiLink 形成 (`src/wikid_steward/core/relinker.py`)**:
   * 登録済みの全用語を辞書ツリー化（Aho-Corasick アルゴリズム等で高速マッチング）。
   * ノート本文中の未リンク単語を自動で `[[用語名]]` に変換し、ナレッジグラフの網の目を自動で編み上げます。
3. **起動タイミング**:
   * Staging から Wiki への昇格プロモート時 (`promoter.py`) に自動統合。

---

### 【Task 3-1】 Qdrant ベクトル DB 統合 ＆ Wiki グラフ拡張検索 (`wikid-steward search`)

#### 概要
単なる断片的なベクトル類似度計算（従来の RAG）を超え、**ヒットしたノートから `[[用語名]]` やバックリンクを自律的に 1～2 ホップ辿ってコンテキストを自動集約する「Wiki グラフ拡張検索」**を構築します。

#### 詳細仕様
1. **Qdrant ベクトルインデクサー (`src/wikid_steward/vector/indexer.py`)**:
   * `wiki/` 配下の全ノート、VLM 画像日本語要約文、HTML `<table>` 表、OKF Frontmatter を埋め込みベクトル化（FastEmbed / sentence-transformers / OpenAI 等）。
   * `wikid-steward index` コマンドで増分・変更検知更新。
2. **Wiki グラフ拡張検索エンジン (`src/wikid_steward/vector/searcher.py`)**:
   * **ステップ 1 [ベクトル & ハイブリッド検索]**: クエリに最も近い主要ノートを検索ヒット。
   * **ステップ 2 [WikiLink Traversal]**: ヒットしたノート内の `[[用語名]]` (Glossary) や参照元バックリンクを 1～2 ホップ走査して周辺定義・文脈を抽出。
   * **ステップ 3 [ナレッジ統合回答生成]**: 主要ノート ＋ 用語定義 ＋ 関連図表 VLM 注記を統合し、構造化された全体レポートとして回答を出力。
3. **CLI コマンド**:
   * `wikid-steward search "検索クエリ"`

---

### 【Task 3-2】 動的 MOC (Map of Content) 生成 ＆ OKF リント (`wikid-steward lint`)

#### 概要
ナレッジベース全体の健全性を常時監視し、カテゴリごとの総括マップノート (Map of Content) を動的メンテナンスします。

#### 詳細仕様
1. **動的 MOC ジェネレーター (`src/wikid_steward/core/moc_generator.py`)**:
   * `wiki/llm/index.md`, `wiki/drawings/index.md` など、カテゴリごとの大系目次マップを自動生成。
   * ドキュメント一覧、最新更新日、含まれる主要用語、VLM 画像アセット数を可視化。
2. **OKF リント ＆ リンクチェッカー (`src/wikid_steward/core/linter.py`)**:
   * **リンク切れ検証**: `![alt](assets/...)` 画像パスや内部リンクの切断を 100% チェック。
   * **Frontmatter チェック**: OKF 規格 (`id`, `title`, `source`, `provenance`) の欠損を検出。
3. **CLI コマンド**:
   * `wikid-steward moc`
   * `wikid-steward lint`

---

## 3. 開発フェーズ ＆ ロードマップ

| フェーズ | マイルストーン | 主要成果物 | 予定期間 |
| :--- | :--- | :--- | :--- |
| **Phase 3-0** | 用語自動抽出 ＆ WikiLink 相互リンク形成 | `glossary.py`, `relinker.py`, 単体・結合テスト | Step 1 |
| **Phase 3-1** | Qdrant ベクトル DB 統合 ＆ Wiki グラフ拡張検索 | `indexer.py`, `searcher.py`, CLI `wikid-steward search` | Step 2 |
| **Phase 3-2** | 動的 MOC 生成 ＆ OKF リント | `moc_generator.py`, `linter.py`, CLI `wikid-steward lint` | Step 3 |

---

## 4. Definition of Done (完了定義)

1. **テスト合格**: すべての新機能に対し、`uv run pytest` で 100% PASS すること。
2. **実データ検証**: 本物の arXiv 論文および図面 PDF を用いた E2E インジェスト・検索・リントが成功すること。
3. **ドキュメント・Git 同期**: 本仕様書および OKF ナレッジドキュメント (`Docs/`) が最新化され、Git リモートリポジトリへクリーンに同期されていること。

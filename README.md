# wikid-steward

> **LLM Wiki Reboot Engine & Knowledge Steward (v7.0)**  
> GFM & OKF v0.2 完全対応・アセット空間隔離・自律協調版  
> プレーンな Markdown、Git、超軽量 CLI、SimpleWiki を組み合わせ、外部ベクトル DB や重厚なフレームワークに依存せず、自律成長型ナレッジネットワークを低摩擦で構築・維持するナレッジ管理エンジン。

---

## 🌟 主な特徴 (Key Features)

* **OKF v0.2 適合スキーマ & GFM (GitHub Flavored Markdown) 完全準拠**:
  * ナレッジのメタデータ（`type`, `status`, `generated.by`, `verified`, `sources`, `stale_after`）を OKF v0.2 に完全準拠。
  * GitHub UI やあらゆる Markdown エディタで直接開いてもリンク・数式・Mermaid・テーブルが崩れない高ポータビリティ設計。
* **「## 📝 手書きメモ」の絶対死守（ガードレール）**:
  * `<!-- HUMAN BEGIN --> ... <!-- HUMAN END -->` の HTML コメントタグによる二重防壁で、AI による自律コンパイルや逆合成時にも現場メモが 100% 破壊されずに安全にマージ・維持されます。
* **スタブ専用フォルダ (`wiki/stubs/`) への隔離と二段階昇格ライフサイクル**:
  * リンク切れ（赤リンク）を検知すると、自動で `wiki/stubs/{slug}.md` に隔離起票。
  * バックリンク文脈からの自動逆合成完了、または人間による査読承認で本番ディレクトリ（`wiki/concepts/` 等）へ自動移動（昇格）。
* **バックリンク文脈からの「用語定義・解説レジュメ」自動逆合成 (Knowledge Retro-Compilation)**:
  * 被リンクが $N$ 件（デフォルト: `3`）以上集まった未定義用語に対し、組織内の使われ方から LLM が固有の解説ページを後追いで自動生成。
  * **AI 循環コピー汚染遮断フィルター**: 未査読の AI 下書きノートをスキャン対象から 100% 除外してハルシネーションの連鎖を防止。
* **Searcher Protocol & Qdrant ベクトル検索 ＋ PageRank ブースト ＋ 自動フォールバック**:
  * Qdrant ベクトル DB 連携時に filelock によるプロセス間排他制御を実施。
  * インデックス作成時に `[[WikiLink]]` 接続グラフから PageRank スコアを事前計算し Payload キャッシュ。類似度＋PageRank ブースト検索を提供。
  * Qdrant 非依存環境や障害時には、Searcher Protocol 経由で軽量ファイルベース検索エンジンへ即座に自動フォールバック。
* **FastMCP 連携モジュール (`wikid-steward mcp`)**:
  * FastMCP を採用し、LLM クライアント（Claude Desktop 等）から `wiki://` リソースの閲覧やナレッジ操作ツール（`search`, `compile_stub`, `lint`, `moc` 等）を直接呼び出し可能。
* **ネスト破綻を回避する堅牢型 WikiRelinker**:
  * コードブロック、インラインコード、数式ブロック、HTML テーブル、手書きメモ、画像パスを多層保護し、大見出し（`##`）セクションごとに初出1回のみ安全に `[[WikiLink]]` 化。
* **Git 協調・ブランチ & PR 協調モデル**:
  * AI 自動監視プロセスは直接 `main` ではなく `steward/auto-compiler` ブランチにコミット・プッシュし、人間とのローカル編集衝突（デッドロック）を完全に解消。`[skip ci]` による CI 無限ループも防止。

---

## 🛠️ インストール ＆ セットアップ

本プロジェクトは **`uv`** (Python 3.12+) を標準パッケージマネージャーとして使用します。

```bash
# リポジトリのクローン
git clone https://github.com/chottokun/wikid-steward.git
cd wikid-steward

# 依存関係のセットアップ
uv sync
```

---

## 🚀 CLI コマンドガイド (Usage)

### 1. ドキュメントの OKF v0.2 Markdown 群へのコンパイル (`compile`)
```bash
# 単一ファイル（PDF, DOCX, PPTX, XLSX, Markdown等）を OKF v0.2 Markdown群にコンパイル
uv run wikid-steward compile path/to/document.pdf

# 即座に stable ステータスとして生成し、査読者ログを付与
uv run wikid-steward compile path/to/document.pdf --auto-stable --reviewer "human:nobuhiko"

# 原本リンクを非表示にし、原本バイナリを sources/ にコピー保存しない（社外秘対応）
uv run wikid-steward compile secret.pdf --hide-source-links --no-save-source

# ディレクトリ内の一括コンパイル（用語抽出をスキップして高速実行）
uv run wikid-steward compile ./documents_dir/ --no-extract-terms
```
`_raw/{slug}.md` への生Markdown配置、`wiki/concepts/` への用語・概念ノート群の自動分解、画像アセットの名前空間隔離、WikiLink相互接続を実行します。

### 2. リアルタイム監視デーモンの起動 (`run`)
```bash
uv run wikid-steward run
```
`_raw/`（原本投入）および `staging/`（承認待機）をリアルタイムに監視・自動処理します。

### 3. 未定義用語スタブの自動逆合成 (`compile-stub`)
```bash
uv run wikid-steward compile-stub "PID制御"
# 強制逆合成 (閾値未満でも実行)
uv run wikid-steward compile-stub "PID制御" --force
```
蓄積されたバックリンク文脈から用語定義レジュメを自動合成し、`wiki/stubs/` から `wiki/concepts/` へ昇格移動します。

### 4. 人間査読ログの記録と昇格 (`review`)
```bash
uv run wikid-steward review wiki/stubs/system-architecture.md --reviewer "human:nobuhiko"
```
フロントマターに査読者ログ (`verified`) を追記し、`status: stable` へ昇格させます。

### 5. Git コンフリクトの自動解決 (`resolve`)
```bash
uv run wikid-steward resolve wiki/concepts/sample.md
```
ファイル内の Git 衝突マーカー（`<<<<<<<` 等）を検知し、手書きメモを保護しながら文脈を自動マージします。

### 6. Wiki ナレッジグラフ検索 (`search`)
```bash
# 自動判定 (auto) - Qdrant ベクトル検索 ＋ PageRank ブースト ＋ フォールバック
uv run wikid-steward search "PID制御とフィードバック"

# バックエンドの明示指定 (--backend auto | qdrant | lightweight)
uv run wikid-steward search "PID制御" --backend lightweight
```
OKF メタデータ、Qdrant ベクトル類似度、事前計算 PageRank スコア、および 1-Hop `[[WikiLink]]` 巡回により、関連用語と統合回答を出力します。

### 7. FastMCP サーバーの起動 (`mcp`)
```bash
uv run wikid-steward mcp
```
FastMCP サーバーを起動し、Claude Desktop や各種 LLM エージェントとの対話的統合を提供します。

### 7. ナレッジ健全性監査 ＆ セルフヒーリング (`lint`)
```bash
# 監査およびスタブ自動起票
uv run wikid-steward lint --auto-stub

# 警告・タイポサジェストのみ表示 (スタブ作成なし)
uv run wikid-steward lint --dry-run
```
リンク切れ、Frontmatter 欠損、脚注と sources の不整合スキャン、タイポサジェスト（安全警告のみ）を実行します。

### 8. 動的 MOC (Map of Content) の自動編成 (`moc`)
```bash
uv run wikid-steward moc
```
カテゴリ別の目次インデックス（`index.md`）を自動生成・再編します。

---

## 🧪 テスト & コード品質チェック

```bash
# CI 同等の高速テストスイート（約 5 秒）
uv run pytest -m "not slow"

# Ruff によるコードフォーマット & リンティング
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# 実 PDF 解析（Docling）を含む全テストスイートの実行
uv run pytest
```

---

## 📚 詳細ドキュメント (Documentation)

アーキテクチャ設計、ライフサイクル仕様、拡張プロファイルなどの詳細は [`docs/`](./docs/index.md) をご参照ください。

* [`docs/architecture/`](./docs/architecture/index.md) - アーキテクチャ設計、Linter、検索エンジン、動的型定義
* [`docs/domain/`](./docs/domain/index.md) - ナレッジライフサイクル、OKF v0.2 仕様、用語集同期
* [`docs/infrastructure/`](./docs/infrastructure/index.md) - リアルタイム監視デーモン、Qdrant ベクトル検索


# wikid-steward

> **LLM Wiki Reboot Engine & Knowledge Steward (v5.0)**  
> 原本ドキュメント（PDF/DOCX/PPTX/XLSX等）から高精度な構造化 Markdown とアセットを自動抽出・カプセル化し、VLM画像要約、用語自動抽出、WikiLink 相互結合、Qdrant グラフ拡張検索、動的 MOC、およびセルフヒーリング健全性監査を統括する次世代ナレッジ管理エンジン。

---

## 🌟 主な特徴 (Key Features)

* **4層ナレッジ・ライフサイクル管理**:
  * `_raw/` (投入) ➔ `staging/` (検証) ➔ `wiki/` (公開 Vault) & `raw_sources/` (原本退避)
  * 原本バイナリを `wiki/`（Obsidian Vault）に混入させず、Git リポジトリの軽量性を維持。
* **VLM (Vision Language Model) による画像日本語自動要約**:
  * Docker 上の Ollama (Ollama / OpenAI 互換 API) と連携し、図表やCAD図面の内容を日本語で高度に自動解釈・要約。
* **LLM 用語自動抽出 (`GlossaryExtractor`) ＆ 堅牢型 WikiRelinker (`relinker.py`)**:
  * 本文から専門用語・核心概念を自動検出し `wiki/glossary/{slug}.md` を自動作成。
  * セグメント分離 ＋ 1パス最長一致置換アルゴリズムにより、**ネスト破綻 `[[[[...]]]]` や過剰リンクを 100% 回避して未リンク単語を `[[用語名]]` に自動相互結合**。
* **Qdrant ベクトル DB 統合 ＆ Wiki グラフ拡張検索 (`wikid-steward search`)**:
  * 単なるベクトル類似度検索を超え、ヒューマン/AIが編み上げた **`[[用語名]]` やバックリンクを 1-Hop 自律巡回して前提定義・背景知識を一括合成したレポート回答** を出力。
* **動的 MOC (Map of Content) 自動編成 (`wikid-steward moc`)**:
  * ドキュメントの追加・更新に応じて、カテゴリ別の体系的目次マップ (`index.md`) を AI が動的編み直し。
* **ナレッジ健全性監査 ＆ セルフヒーリング (`wikid-steward lint`)**:
  * 壊れた画像パス `![alt](assets/...)`、Frontmatter 欠損、孤立ノートを全自動検出。
* **網羅的ハイブリッド設定システム (`config.yaml` ＋ `.env`)**:
  * LLM 接続先、VLM オプション、4層パス、プロファイルポリシーを外部設定ファイルから全カスタマイズ可能。

---

## 🛠️ インストール ＆ セットアップ

本プロジェクトは **`uv`** (Python 3.12+) を標準パッケージマネージャーとして使用します。

```bash
# リポジトリのクローン
git clone https://github.com/chottokun/wikid-steward.git
cd wikid-steward

# 依存関係のセットアップ (docling-lib, openai, qdrant-client, fastembed, pillow 等)
uv sync
```

---

## 🚀 CLI コマンドガイド (Usage)

### 1. リアルタイム監視デーモンの起動 (`run`)
```bash
uv run wikid-steward run
```
`_raw/`（原本投入）および `staging/`（承認待機）をリアルタイムに監視・自動処理します。

### 2. LLM-Wiki グラフ拡張検索 (`search`)
```bash
uv run wikid-steward search "What is LLM-as-a-judge evaluation?"
```
Qdrant ベクトル検索 ＋ 1-Hop WikiLink グラフ巡回 ＋ `gemma4:latest` を統合し、用語定義や背景文脈が整理された回答レポートを返します。

### 3. 動的 MOC (Map of Content) の一括自動更新 (`moc`)
```bash
uv run wikid-steward moc
```
`wiki/` 内の全サブカテゴリに `index.md` (目次ツリー・ドキュメント一覧) を動的生成・最新化します。

### 4. ナレッジベース健全性監査 (`lint`)
```bash
uv run wikid-steward lint
```
画像リンク切れ、Frontmatter 欠損、孤立ノートを走査し、健全性を 100% 保証します。

---

## ⚙️ 外部設定 (`config.yaml` ＆ `.env`)

環境変数 (`.env`) > `config.yaml` > デフォルト値 の優先順位で読み込まれます。

```yaml
# config.yaml
llm:
  provider: "ollama"
  base_url: "http://localhost:11434/v1"
  model: "gemma4:latest"

vlm:
  enabled: true
  provider: "ollama"
  model: "qwen3.5:4b"

paths:
  raw_dir: "_raw"
  staging_dir: "staging"
  wiki_dir: "wiki"
```

---

## 🧪 テスト実行

```bash
# 全 38 件の単体・結合テストの実行
uv run pytest
```

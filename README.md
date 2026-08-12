# wikid-steward

> **LLM Wiki Simple Reboot Engine (v5) & Knowledge Manager**  
> 原本ドキュメント（PDF/DOCX/PPTX/XLSX等）から高精度な構造化 Markdown とアセットを自動抽出・カプセル化し、人間介在型レビュー (HITL) と不変のトレーサビリティを両立するナレッジ管理システム。

---

## 🌟 主な特徴 (Key Features)

* **4層ナレッジ・ライフサイクル管理**:
  * `_raw/` (投入) ➔ `staging/` (検証) ➔ `wiki/` (公開) & `raw_sources/` (退避)
  * 原本バイナリを `wiki/`（Obsidian Vault）に混入させず、Git リポジトリの軽量性を維持。
* **決定論的 Slug 命名規則**:
  * Unicode NFC 正規化（macOS NFD 濁点分解の解消）、日本語保護、UTF-8 100 バイト安全切り詰め。
* **高精度構造化パース (`chottokun/docling-markdown-generator` 直結)**:
  * Docling v2.x をベースに、結合セルを維持した HTML `<table>` 出力、LaTeX 数式認識 (`$$ ... $$`)。
* **2層ハイブリッドメタデータ (層A + 層B)**:
  * **【層A】 Markdown Frontmatter**: Google OKF v0.2 スキーマ適合の可変メタデータ。
  * **【層B】 PNG `tEXt` チャンク**: Pillow を用いた画像バイナリ内部への不変メタデータ焼き込み (`llm_wiki_meta`)。
* **3段階パースプロファイル制御 (Parse Profile Control)**:
  * 優先度1: サイドカー YAML (`file.yaml`) ➔ 優先度2: フォルダ名判定 ➔ 優先度3: 完全デフォルト。
  * **論文プロファイル (`paper`)**: OCR オフ、デジタル精度・LaTeX重視。
  * **図面プロファイル (`drawing`)**: OCR オン、高解像度 3.0 倍切り出し、**SBOM (部品構成表) の構造化 HTML `<table>` 自動抽出**。
* **拡張可能なカスタムハンドラー基盤 (`BaseProfileHandler`)**:
  * 独自パターンに応じたパース後処理コードやカスタムアセット抽出ロジックをプラグイン形式で簡単に追加・オーバーライド可能。

---

## 🛠️ インストール ＆ セットアップ

本プロジェクトは **`uv`** (Python 3.12+) を標準パッケージマネージャーとして使用します。

```bash
# リポジトリのクローン
git clone https://github.com/chottokun/wikid-steward.git
cd wikid-steward

# 依存関係のセットアップ (docling-lib, pillow, watchdog 等)
uv sync
```

---

## 🚀 クイックスタート (使用方法)

### 1. リアルタイム監視デーモンの起動

```bash
uv run wikid-steward run
```

デーモンが常駐し、`_raw/` ディレクトリ（原本投入）および `staging/` ディレクトリ（昇格判定）をリアルタイムに監視します。

### 2. ドキュメントの投入から昇格までの流れ

1. **原本の投入**:
   * 原本 PDF などを `_raw/` 配下に配置（例: `_raw/drawings/component.pdf` や `_raw/papers/paper.pdf`）。
   * サイドカー指定を行いたい場合は横に `component.yaml` を配置。
2. **Staging での検証**:
   * パース結果が `staging/` 配下にノートおよび `assets/` フォルダとして自動生成されます。
3. **人間によるレビュー (HITL) ＆ 昇格**:
   * Obsidian や VS Code で `staging/` 内のノートを開き、YAML ヘッダーを `status: "reviewed"` に書き換えて保存。
   * デーモンが 1 秒のデバウンス窓で検知し、ノートとアセットが `wiki/` へ物理移動 (`shutil.move`) され、原本が `raw_sources/` へ自動退避移動・Git コミットされます。

---

## 🧩 カスタムプロファイルハンドラーの追加方法

特定のパターン（独自のCAD図面、社内仕様書など）に向けたカスタムコードを追加したい場合、`BaseProfileHandler` を継承して登録します。

```python
from wikid_steward.core.handlers import BaseProfileHandler, register_profile_handler

class MyCustomHandler(BaseProfileHandler):
    def post_process_markdown(self, markdown_text: str, profile_name: str) -> str:
        # カスタムパース後処理コード
        header = f"> [!tip] 📌 カスタムプロファイル ({profile_name}) 処理済み\n\n"
        return header + markdown_text

# プロファイル名と紐づけて登録
register_profile_handler("my_pattern", MyCustomHandler())
```

※ 詳細なテンプレートとガイドは [`Docs/architecture/handlers.md`](file:///home/nobuhiko/Project/wikid-steward/Docs/architecture/handlers.md) をご覧ください。

---

## 🧪 テストの実行

```bash
# 全単体・統合テストの実行 (Pytest)
uv run pytest
```

`.gitignore` により、原本 PDF やテスト用一時生成物は Git リポジトリに入らないよう厳格に防護されています。

---

## 📚 ドキュメント (OKF 仕様)

* 📄 [Docs/index.md](./Docs/index.md) - ナレッジベース最上位インデックス
* 📄 [Docs/domain/lifecycle.md](./Docs/domain/lifecycle.md) - 4層ナレッジ・ライフサイクル仕様
* 📄 [Docs/domain/slug.md](./Docs/domain/slug.md) - スラッグ生成・規格化命名規則
* 📄 [Docs/architecture/parser.md](./Docs/architecture/parser.md) - Docling 統合仕様
* 📄 [Docs/architecture/metadata.md](./Docs/architecture/metadata.md) - 2層メタデータ設計
* 📄 [Docs/architecture/handlers.md](./Docs/architecture/handlers.md) - カスタムハンドラー追加ガイド

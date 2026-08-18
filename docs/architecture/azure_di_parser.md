---
type: "Architecture Decision"
title: "Azure Document Intelligence 連携 ＆ 構造化 HTML テーブル自動変換 設計仕様"
description: "Azure Document Intelligence (prebuilt-layout) を用いた高速クラウドパースと、セル結合を含む複雑な表のセマンティック HTML <table> 自動変換アーキテクチャ仕様"
status: "draft"
generated:
  by: "agent/gemini-3.7-flash"
  at: "2026-08-17T22:45:00Z"
sources:
  - id: "azure-di-docs"
    resource: "https://learn.microsoft.com/azure/ai-services/document-intelligence/"
    title: "Azure Document Intelligence Documentation"
tags:
  - architecture
  - parser
  - azure_di
  - ocr
  - table_structure
---

# Azure Document Intelligence 連携 ＆ 構造化 HTML テーブル自動変換 設計仕様

本ドキュメントは、ローカル実行型パーサー（Docling）に加え、Microsoft Azure の **Azure Document Intelligence (旧 Form Recognizer)** をクラウドパーサープロバイダーとして統合し、複雑な表構造（セル結合・段組ヘッダー）をセマンティックな HTML `<table>` として高精度に Markdown へ埋め込むアーキテクチャ設計仕様書である。

---

## 1. システム構成とデュアルパーサー方針

`wikid-steward` のパーサー層（`src/wikid_steward/core/parser.py`）を抽象化し、ローカル環境（Docling）とクラウド環境（Azure DI）を用途・リソースに応じてシームレスに切り替え可能にする。

```
┌────────────────────────────────────────────────────────┐
│                   原本ドキュメント                     │
│           (PDF, DOCX, PPTX, XLSX, 画像スキャン)        │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│         パーサー・プロバイダー・ルーティング           │
│        (config.yaml または profile.parser_provider)     │
└─────────────┬────────────────────────────┬─────────────┘
              ▼                            ▼
┌───────────────────────────┐┌───────────────────────────┐
│     Docling (ローカル)    ││   Azure DI (クラウド)     │
│  ・GPU/CPU 完全オフライン ││  ・秒速・低負荷処理       │
│  ・ローカルOSSモデル      ││  ・高精度日本語OCR・表解析│
└─────────────┬─────────────┘└─────────────┬─────────────┘
              │                            │
              └─────────────┬──────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│     複雑表の HTML <table> 自動変換 ＆ Markdown統合     │
│   ・単純な表 ➔ GFM パイプテーブル                      │
│   ・セル結合表 ➔ 構造化 HTML <table> 表 (rowspan/colspan)│
│   ・画像アセット ➔ assets/{slug}/ への自動抽出         │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│       OKF v0.2 Markdown 群 (Wiki / _raw / concepts)    │
└────────────────────────────────────────────────────────┘
```

---

## 2. 複雑な表の HTML `<table>` 自動変換アルゴリズム

Azure Document Intelligence の `prebuilt-layout` モデルは、ドキュメント内の全テーブルを `analyze_result.tables` として構造化オブジェクト（行数、列数、セルごとの `row_index`, `column_index`, `row_span`, `column_span`, `content`, `kind`）で返却する。

### 2.1 表形式の自動判定ロジック
各テーブルを走査し、以下の基準で出力形式を自動分岐する：

```python
def is_complex_table(table) -> bool:
    """セル結合（row_span > 1 または column_span > 1）が存在するか判定"""
    for cell in table.cells:
        if (cell.row_span and cell.row_span > 1) or (cell.column_span and cell.column_span > 1):
            return True
    return False
```

1. **単純な表（`is_complex_table == False`）**:
   * 標準的な **GFM パイプテーブル (`| 列1 | 列2 |`)** として Markdown に埋め込む。
2. **複雑な表（`is_complex_table == True` または プロファイルで `extraction_format: "html_table"` 指定時）**:
   * **HTML `<table>` 表** へ自動変換する。

### 2.2 HTML `<table>` 変換アルゴリズム

```python
def convert_azure_table_to_html(table) -> str:
    """Azure DI のテーブルオブジェクトをセマンティックな HTML <table> 文字列に変換する"""
    grid = {}
    row_count = table.row_count
    col_count = table.column_count

    # 1. セルを行・列インデックスごとにマッピング
    for cell in table.cells:
        grid[(cell.row_index, cell.column_index)] = cell

    rows_html = []
    for r in range(row_count):
        cells_html = []
        for c in range(col_count):
            if (r, c) not in grid:
                continue
            cell = grid[(r, c)]
            
            tag = "th" if getattr(cell, "kind", "") == "columnHeader" or r == 0 else "td"
            attrs = []
            if cell.row_span and cell.row_span > 1:
                attrs.append(f'rowspan="{cell.row_span}"')
            if cell.column_span and cell.column_span > 1:
                attrs.append(f'colspan="{cell.column_span}"')
            
            attr_str = (" " + " ".join(attrs)) if attrs else ""
            content_clean = cell.content.replace("\n", "<br>")
            cells_html.append(f"<{tag}{attr_str}>{content_clean}</{tag}>")
        
        rows_html.append("  <tr>" + "".join(cells_html) + "</tr>")

    table_html = (
        '<table border="1">\n'
        "<tbody>\n"
        + "\n".join(rows_html) + "\n"
        "</tbody>\n"
        "</table>"
    )
    return table_html
```

---

## 3. ガードレールとの完全整合（WikiRelinker 連携）

`wikid-steward` のコア機能である `WikiRelinker` は、`<table>...</table>` の HTML タグブロックを **最優先保護セグメント（Protected Segment）** として隔離します。

* **メリット**:
  * 生成された HTML テーブル内のタグや属性（`rowspan="2"` 等）が AI 置換処理によって破壊されるリスクがゼロ。
  * テーブル内の専門用語のみが人間向けに安全に表示され、GitHub UI や SimpleWiki 上で 100% 崩れずにレンダリングされる。

---

## 4. 設定仕様 (`config.yaml` / `.env`)

### 4.1 環境変数 (`.env`)
```bash
# Azure Document Intelligence 認証情報
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="https://<your-resource-name>.cognitiveservices.azure.com/"
AZURE_DOCUMENT_INTELLIGENCE_KEY="YOUR_AZURE_KEY"
```

### 4.2 設定ファイル (`config.yaml`)
```yaml
parser:
  provider: "docling"          # デフォルト: "docling" | "azure_di"
  azure_di:
    endpoint: "${AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT}"
    api_key: "${AZURE_DOCUMENT_INTELLIGENCE_KEY}"
    model_id: "prebuilt-layout" # prebuilt-layout | prebuilt-read | prebuilt-document
    output_complex_tables_as_html: true
```

### 4.3 プロファイル設定 (`profiles/drawing_sbom.yaml`)
```yaml
doc_type: "Drawing SBOM"
parser_provider: "azure_di"     # このプロファイルのみ Azure DI を強制利用
extraction_format: "html_table"
```

---

## 5. 将来の実装クラス設計 (`src/wikid_steward/core/azure_di_parser.py`)

Azure DI 環境が準備できた際に組み込むクラスのテンプレート設計：

```python
from pathlib import Path
from typing import Any
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

class AzureDocumentIntelligenceParser:
    """Azure Document Intelligence (prebuilt-layout) を利用した

    高精度ドキュメント解析 ＆ 構造化 Markdown 生成パーサー。
    """

    def __init__(self, endpoint: str, api_key: str, model_id: str = "prebuilt-layout"):
        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key),
        )
        self.model_id = model_id

    def parse_to_markdown(self, file_path: Path, output_html_tables: bool = True) -> str:
        """ファイルを解析し、複雑な表を HTML <table> に置換した Markdown を生成する。"""
        with open(file_path, "rb") as f:
            poller = self.client.begin_analyze_document(
                model_id=self.model_id,
                body=f,
                output_content_format="markdown",
            )
        result = poller.result()
        raw_markdown = result.content or ""

        if output_html_tables and result.tables:
            # 複雑な表の置換処理を適用
            raw_markdown = self._replace_complex_tables(raw_markdown, result.tables)

        return raw_markdown

    def _replace_complex_tables(self, markdown: str, tables: list[Any]) -> str:
        # テーブルオブジェクトを走査し、セル結合を持つ表を HTML <table> に置換
        ...
        return markdown
```

---

## 6. まとめ
本設計により、将来 Azure DI が利用可能になった際、`azure-ai-documentintelligence` パッケージを追加し `AzureDocumentIntelligenceParser` を差し込むだけで、既存の OKF v0.2 コンパイラや WikiRelinker、手書きメモ保護ガードレールと 100% 互換性を保ったまま即座に運用を開始できます。

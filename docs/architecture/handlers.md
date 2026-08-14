---
type: architecture
title: カスタムプロファイルハンドラー作成・追加ガイド ＆ コードテンプレート
sources: src/wikid_steward/core/handlers.py
description: wikid-steward において独自のパース後処理やカスタム抽出ロジックを持つ追加ハンドラーを作成・登録する手順とコードテンプレート
tags: [handler, plugin, template, architecture]
---

# カスタムプロファイルハンドラー作成・追加ガイド

本ドキュメントは、`wikid-steward` において特定のドキュメントパターン（独自のCAD図面、社内仕様書、Excel集計表、発表スライドなど）に向けた**カスタムハンドラー**を自作し、システムに登録・組み込むためのガイドラインおよびコードテンプレートである。

---

## 1. カスタムハンドラーの構成要素

カスタムハンドラーは `BaseProfileHandler` を継承して作成し、主に以下の2つのフックポイント（オーバーライド可能なメソッド）を持つ。

1. **`post_process_markdown(markdown_text: str, profile_name: str) -> str`**
   - Docling パース直後に呼び出され、Markdown テキストに対する独自の変換・クリーンアップ・コールアウト挿入・構造化表（BOM/SBOM等）の生成コードを差し込む。
2. **`process_custom_assets(conv_result: Any, assets_dir: Path) -> list[dict]`**
   - パース時に切り出される図表アセットに対し、特定パターンの追加クロップや特殊メタデータの抽出を行う。

---

## 2. 追加ハンドラーの実装 3 ステップ

### Step 1: `BaseProfileHandler` を継承したクラスの作成
独自のパース加工コードをクラスとして実装します。

### Step 2: `register_profile_handler` による登録
作成したハンドラーを、対象のプロファイル名（例: `"my_custom_pattern"`）と紐づけて登録します。

### Step 3: サイドカー YAML または フォルダ名での呼び出し
- サイドカー: 原本の横に `file.yaml` を置き `profile: "my_custom_pattern"` を記述。
- フォルダ名: `_raw/my_custom_pattern/` フォルダ配下に原本を投入。

---

## 3. コピペで使えるカスタムハンドラー・コードテンプレート

以下を参考に、新しいハンドラーファイルを `src/wikid_steward/core/handlers/` またはプロジェクト内のコードにコピー＆ペーストしてご利用ください。

```python
"""
カスタムプロファイルハンドラーのテンプレート
ファイル名例: src/wikid_steward/handlers/my_custom_handler.py
"""

from pathlib import Path
from typing import Any
from wikid_steward.core.handlers import BaseProfileHandler, register_profile_handler
from wikid_steward.core.profiles import ParseProfile, ParseProfile, register_profile_handler


class MyCustomHandler(BaseProfileHandler):
    """【テンプレート】独自ドキュメントパターン向けカスタムハンドラー"""

    def post_process_markdown(
        self, markdown_text: str, profile_name: str
    ) -> str:
        """Docling がパースした Markdown 本文に対するカスタム加工ロジック"""
        
        # 1. 独自テキスト抽出やフィルタリング
        extracted_info = self._analyze_custom_notes(markdown_text)

        # 2. カスタムコールアウトや構造化表ブロックの生成
        custom_header_block = (
            f"> [!tip] 📌 カスタムプロファイル ({profile_name}) 処理済み\n"
            f"> 解析結果: {extracted_info}\n\n"
        )

        # 3. 加工後の Markdown を返却
        return custom_header_block + markdown_text

    def _analyze_custom_notes(self, text: str) -> str:
        """独自パース分析コード（例: 特定キーワードの集計など）"""
        lines = [line for line in text.splitlines() if "NOTE" in line.upper()]
        return f"検出された Note 数: {len(lines)} 件"

    def process_custom_assets(
        self, conv_result: Any, assets_dir: Path
    ) -> list[dict[str, Any]]:
        """特殊な画像クロップやカスタムアセットメタデータを追加抽出するコード"""
        custom_assets = []
        # 必要に応じて独自アセット処理を記述
        return custom_assets


# ==============================================================================
# ハンドラーの自動登録
# ==============================================================================
# "my_pattern" プロファイルとして登録（サイドカー file.yaml の profile: my_pattern で起動可能）
my_handler_instance = MyCustomHandler()
register_profile_handler("my_pattern", my_handler_instance)
```

---

## 4. 登録済み標準ハンドラー一覧

* `PaperHandler` (`profile: "paper"`): 論文・文献用標準ハンドラー
* `DrawingHandler` (`profile: "drawing"`): CAD/図面用 SBOM 表自動構築ハンドラー
* `SpreadsheetHandler` (`profile: "spreadsheet"`): 表計算データ用ハンドラー
* `PresentationHandler` (`profile: "presentation"`): スライド発表資料用ハンドラー

# 技術参照仕様書: docling-markdown-generator 統合とアセットカプセルパース仕様 - v5 (一貫性確保・決定版)

本ドキュメントは、**`wikid-steward`** の高精度データ抽出バックボーンとして、**`docling-markdown-generator`** を統合・活用するための技術仕様および実装計画をまとめた参照用システム文書（v5）である。

アセットの「すぐ横」配置への完全なカプセル化ルール、および再実行時における「アセットフォルダ完全クリーンアップ」による冪等性確保、およびMVP段階におけるローカルVLM呼び出しの一時バイパス（無効化）を決定論的に仕様化する。

また、本プロジェクトが採用する `chottokun/docling-markdown-generator` は開発者（ユーザー）自身によって直接管理・メンテナンスされているため、必要に応じてエンジンのコード自体を柔軟に改修・最適化可能である。

---

## 1. 統合の目的と選定背景

不変の一次ソース（`_raw/`）から、どれだけ高精度かつセマンティクス（意味・文脈）を維持した状態でMarkdown情報を抽出できるかは、LLM Wikiのナレッジ品質に直結する。

`docling-markdown-generator`（最新の **Docling v2.x** を内包）を採用することで、以下の技術的優位性を確保する。
1. **外部依存の排除**: LibreOffice不要で、PDFに加え Word（`.docx`）、PowerPoint（`.pptx`）、Excel（`.xlsx`）ファイルを外部プロセスなしでネイティブかつ高速に処理可能。
2. **スレッドセーフな非同期設計**: 解析エンジンの再利用（シングルトン化）による初期化コストの低減、非同期ブロッキングI/Oの最適化により、デーモンのバックグラウンド並行処理に完全に適合。
3. **セキュリティの強化**: パストラバーサル（Path Traversal）防御、最大アップロードサイズ制御によるDoS保護が組み込まれており、外部文書を自律処理する際の堅牢性が極めて高い。

---

## 2. 高精度パースと唯一ルールに基づくアセットカプセル配置仕様

`chottokun/docling-markdown-generator` を用いたパース段階において、テキスト・複雑な表・数式を適切に分離しつつ、アセットを指定の唯一ルールへ適合させて出力する。

### ① 複雑な表（テーブル）構造のHTML出力
*   **仕様**: 結合セルや複数ヘッダーを含む複雑な表を、セルの結合属性（`colspan`, `rowspan`）を維持したHTML形式のテーブル表現（`<table>`）として忠実に書き出す [106]。
*   **メリット**: 標準のMarkdownテーブル記法では表現できない多次元の表データを完全に維持し、LLMがテーブル内の数値を誤認して編纂マージすることを防止する [106]。

### ② 数式およびソースコードの自動認識
*   **仕様**: 数式を自動検出して **LaTeX形式**（`$$ ... $$` や `$ ... $`）へ自動変換する [74, 106]。また、コードブロックは自動分類され、該当するプログラミング言語がシンタックス指定される [74, 106]。

### ③ 唯一ルールに適合する画像クロップ抽出と局所保存（冪等性・衝突回避仕様）
原本 `_raw/{DPIフォルダ構造}/{filename}.pdf` が投入された際、生成されるグローバル一意Slug名（`{DPI構造}_{filename}` ※小文字化、スペース及び禁止文字置換済）に基づき、抽出された画像は必ず以下のカプセル化アセットフォルダ配下に保存する。

*   **Markdownの保存先**: `staging/{DPIフォルダ構造}/{Slug名}.md`
*   **アセットフォルダの真の保存先**: `staging/{DPIフォルダ構造}/assets/{Slug名}/`
*   **画像アセットパス**: `staging/{DPIフォルダ構造}/assets/{Slug名}/{image_id}.png`
*   **画像メタデータパス**: `staging/{DPIフォルダ構造}/assets/{Slug名}/{image_id}.json`

#### 💡 再実行時のアセットクリーンアップ・ロジック（冪等性の担保）
ドキュメントの再投入や更新パースの際、古いPDFの変更により不要になった画像（ゴースト・ファイル）がアセットフォルダ内に残留し、Wikiを汚染するのを防ぐため、以下のクリーンアップを決定論的に実行する。

```python
import os
import shutil

def prepare_clean_assets_dir(target_assets_dir: str):
    """
    画像を切り出す前に、対象のアセットフォルダ（assets/{Slug名}/）が既に存在する場合、
    それを一度完全に物理削除（shutil.rmtree）し、空の状態で再作成する。
    これにより古いPDF世代の不要な切り出し画像（孤立アセット）が残ることを完璧に防ぐ。
    """
    if os.path.exists(target_assets_dir):
        # 既存の古いアセットフォルダを丸ごと削除してクリーンに
        shutil.rmtree(target_assets_dir)
    
    # 階層ごと新規に空のフォルダを作成
    os.makedirs(target_assets_dir, exist_ok=True)
```

---

## 3. `wikid-steward` パースパイプライン API構成（MVP）

パース処理を実行する筋肉モジュール `parser.py` は、`docling-markdown-generator` のPython APIを直接呼び出す。

### ① パイプライン設定仕様
パース処理の最適化と、ハードウェアリソース（RTX 3060 12GB等）の枯渇を避けるため、以下のパイプラインオプション（`PipelineOptions`）を適用する。

```python
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableStructureOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

# PDFパース設定の定義
pdf_options = PdfPipelineOptions()

# OCRのオフ: デジタルPDFの読み込みにおいてハルシネーションを防ぐためOCRは無効化 [42]
pdf_options.do_ocr = False

# 高精度テーブル構造認識の有効化 [42]
pdf_options.do_table_structure = True
pdf_options.table_structure_options = TableStructureOptions(
    mode="accurate"  # セル結合を正確に維持する [43]
)

# 図表（Picture）の自動抽出を有効化 [43]
pdf_options.images_scale = 2.0  # 抽出画像の解像度スケール
pdf_options.generate_picture_images = True

# 📌 ローカルVLM呼び出しの一時ゲート（MVPでは無効化）
# 大判PDFから大量画像が切り出された際、VLMの逐次呼び出しによるVRAM逼迫・遅延・GPU枯渇エラーを避けるため、
# MVPフェーズでは VLMアノテーション生成機能を明示的に False に制限する。
pdf_options.generate_picture_descriptions = False  # VLMによる解説生成はバイパスし、高度版バックログへ延期

# コンバーターのインスタンス化
converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)
    }
)
```

### ② Markdown内画像リンクの「Obsidian標準」相対リンク置換ロジック
パース結果として出力される Markdown ファイル内の画像リンク記述（標準のDoclingが生成する一時パス等）をスキャンし、一律で**「すぐ横」配置に適合する一貫した相対パス**へと置換する処理を `okf_converter.py`（Task 1-3）にて実行する。

*   **置換前（Doclingの一時パスなど）**: `![](file:///tmp/docling/fig1.png)`
*   **置換後（唯一ルール適合リンク）**: `![](assets/{Slug名}/{画像名}.png)` または `![[{assets/{Slug名}/{画像名}.png}]]`

---

## 4. 開発者自身による「エンジン改善」のロードマップ

`chottokun/docling-markdown-generator` はユーザー様自身が直接管理されているリポジトリであるため、以下の**「双方向の最適化」**を継続的に実施して、`wikid-steward` のデータ処理品質を向上させる。

1.  **見出し（Header）マッピングのカスタム最適化**:
    原本PDFのフォントサイズやスタイルに基づく見出し認識を、Obsidianでのアウトライン（MOC）生成に最適化されたH1〜H6のMarkdownレベルへと直接エンジン側でマッピング調整する。
2.  **数式の LaTeX デリミタのカスタム置換**:
    数式のパース結果を、Obsidianが即座にMathJaxで数式レンダリング可能なLaTeX形式（`$$ ... $$` や `$ ... $`）へ適合させるため、エンジンのMarkdownレンダラー内で決定論的に文字列フォーマットを自動チューニングする。
3.  **非同期ブロッキングI/OとVRAM使用のチューニング**:
    常駐デーモンとしてバックグラウンドで並行パースを大量に走らせる中、複数コンテナを立ち上げた際のDoclingエンジンの初期化コストやVRAM競合を最小化するため、パーサーリポジトリ側で非同期セマンティクスを独自に調整する。

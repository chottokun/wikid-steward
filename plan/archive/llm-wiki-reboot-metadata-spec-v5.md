# メタデータ＆フォルダ構造仕様書: wikid-steward 2層ハイブリッドメタデータ詳細仕様 - v5 (一貫性確保・決定版)

本ドキュメントは、**`wikid-steward`** のシンプル・リブート版フォルダ構造、およびポータビリティと不変のトレーサビリティを両立するための**「2層ハイブリッドメタデータ設計（層A＋層B）」**の厳格な物理仕様を定めたものである。

DPI（ディレクトリ階層維持）を踏襲しつつ、Markdownファイル名および画像アセットの物理格納パスルール、NFC正規化および100バイト切り詰めを含む厳格なスラッグ生成規則、人間介在型レビュー（HITL）昇格の厳密ルール、および冪等性・重複回避仕様を一通りに完全固定化する。

---

## 1. 物理配置・命名規則（DPI）の唯一ルール

ナレッジを物理フォルダ（Obsidian Vault）内で人間にとって見やすく整理しつつ、ノート名や画像パスのリネーム・衝突、リンク破綻をプログラムレベルで完全に排除するため、以下の命名および配置ルールをシステム内の唯一の真実（Single Source of Truth）として強制する。

### ① グローバル一意なファイル命名（Slug名物理統一規則）
原本ファイルが `_raw/project-A/sub-component/DWG-2026-X88.pdf` のように配置された場合、生成されるMarkdownファイル名は、物理パス階層をアンダースコアで連結した**「グローバル一意なSlug名」**とする。

*   **Markdownファイル名**: `project-a_sub-component_dwg-2026-x88.md`
*   **物理配置フォルダ（DPIを維持）**: `staging/project-A/sub-component/project-a_sub-component_dwg-2026-x88.md`

#### 💡 スラッグ生成＆規格化アルゴリズム（Python実装仕様）
日本語などのマルチバイト文字を完全に保護しつつ、macOS特有のNFD（濁点分解）問題によるファイル名不一致や、日本語URLエンコード爆発（1文字最大9バイト化）によるOSの255バイト制限クラッシュを決定論的に回避するため、以下の正規化アルゴリズムをデーモン側で強制適用する。

```python
import re
import unicodedata

def generate_slug(relative_path_no_ext: str) -> str:
    """
    _raw/ からの相対パス（拡張子除く）を一意なSlugファイル名に決定論的に変換する。
    Unicode NFC正規化を適用し、日本語等のマルチバイト文字を保護・維持しつつ、
    OSの255バイト制限やURLエンコード爆発を回避するため100バイト以内で安全に切り詰める。
    """
    # 1. Unicode NFC正規化を一律適用（macOS特有のNFD濁点分解によるファイル名ドリフト・Git競合の防止） [377, 402]
    normalized = unicodedata.normalize('NFC', relative_path_no_ext)
    
    # 2. パス区切り文字 (/, \) を一律アンダースコアに置換してフラット化
    normalized = normalized.replace("/", "_").replace("\\\\", "_")
    
    # 3. ASCII文字をすべて小文字化（ケースインセンシティブ対応）
    normalized = normalized.lower()
    
    # 4. OSのファイル名禁止文字、スペース、Obsidian/Markdownのメタ文字を一律ハイフンに置換
    # (日本語などのマルチバイト文字 \w は維持する) [377]
    normalized = re.sub(r'[\s\:\*\?\"\<\>\|\[\]\#\^\,\;\!\&\(\)\@\.\=\+]+', '-', normalized)
    
    # 5. セパレータ文字（アンダースコア、ハイフン）の重複（連続）を1つに整理
    normalized = re.sub(r'[-_]{2,}', '_', normalized)  # 重複セパレータのクリーンアップ
    normalized = re.sub(r'-+', '-', normalized)
    normalized = re.sub(r'_+', '_', normalized)
    
    # 6. 文字列の先頭および末尾の不要なセパレータ（ハイフン、アンダースコア）をトリミング
    normalized = normalized.strip("-_")
    
    # 7. 100バイト切り詰めルール（URLエンコード爆発対策・OS 255バイト制限の絶対防御） [402, 426]
    # マルチバイト文字を文字単位で安全に切り詰めるため、1文字ずつUTF-8エンコード時のサイズを累積計算
    byte_limit = 100
    accumulated_bytes = 0
    truncated_chars = []
    
    for char in normalized:
        char_bytes = len(char.encode('utf-8'))
        if accumulated_bytes + char_bytes > byte_limit:
            break
        truncated_chars.append(char)
        accumulated_bytes += char_bytes
        
    normalized = "".join(truncated_chars).strip("-_")
    
    return normalized
```

*   **例**: `_raw/Project A/Sub-Component/DWG 2026 X88.pdf`  
    ⮕ `project-a_sub-component_dwg-2026-x88.md`
*   **日本語例**: `_raw/プロジェクトA/設計図/DWG 仕様書.pdf`  
    ⮕ `プロジェクトa_設計図_dwg-仕様書.md` (NFC正規化が適用され、日本語部分は完全に美しく維持される)
*   **100バイト切り詰め例**: 非常に深いディレクトリの日本語名（例：`_raw/システム開発/コアモジュール/認証モジュール/ユーザー認証およびシングルサインオンに関する仕様書-第3版.pdf`）は、UTF-8バイトサイズが100バイトを超えた文字の直前で安全にトリミングされ、末尾の不要な記号が削られます。これにより、将来的なURLエンコード時にもOSの255バイト制限に絶対に衝突しません [426]。

#### ⚠️ 既存ファイルとの衝突時の解決方法
もし `_raw/project-A/sub-component/Document.pdf` と `_raw/project-A/sub_component/Document.pdf` のように、元の配置は異なるが、標準化スラッグや100バイト切り詰め制限の結果が完全に一致するファイル（`project-a_sub-component_document`）が同時にインジェストされた場合の衝突解決ルール：
1.  **内容比較（ハッシュチェック）**: 
    生成される構造化MarkdownのSHA-256ハッシュが同一である場合 ⮕ 重複インジェストと判定し、処理を安全にスキップ（1つのファイルのみを残す） [377]。
2.  **別内容の場合（自動サフィックス付与）**:
    内容が異なる場合、末尾に自動インクリメントサフィックス（`-1`, `-2` 等）を付与してファイル名およびYAMLの `id` を決定する。
    *   競合1: `project-a_sub-component_document.md`
    *   競合2: `project-a_sub-component_document-1.md`

---

### ② 画像アセットの「すぐ横」格納パスルール
画像アセットフォルダは、Markdownファイルの物理的な「すぐ横」にある `assets/` ディレクトリ直下に、**MarkdownのSlug名と1対1で対応するフォルダを作成して隔離保管**する。

*   **Markdown's 物理パス**: `.../project-A/sub-component/project-a_sub-component_dwg-2026-x88.md`
*   **アセットフォルダの真の保存先**: `.../project-A/sub-component/assets/project-a_sub-component_dwg-2026-x88/`
*   **画像ファイルのパス**: `.../project-A/sub-component/assets/project-a_sub-component_dwg-2026-x88/fig1.png`
*   **Markdown内の画像参照コード**: `![](assets/project-a_sub-component_dwg-2026-x88/fig1.png)`

---

## 2. 【層A】Markdown YAML Frontmatter（可変メタデータ）

人間がObsidianやVS Code等で容易に編集・閲覧でき、システム制御に用いる可変プロパティである。

### ① スキーマ定義
```markdown
---
id: project-a_sub-component_dwg-2026-x88                       # グローバル一意なSlug名（ファイル名と一致。NFC・100B制限適用済）
title: "DWG-2026-X88 CAD仕様書"
type: "Technical Specification"                                # Google OKF必須: ドキュメントの種類 [310, 315]
path: "project-A/sub-component"                                # Obsidian等の DataviewJS/Bases 用の仮想論理パス

# グラウンディング（出所）とハルシネーション自己汚染防止
source: "raw_sources/project-A/sub-component/DWG-2026-X88.pdf"   # 一意な一次ソース（不変原本）への物理パス
provenance:                                                     # SIGNプロトコル準拠の信頼性評価 [402, 477]
  extracted: 0.90                                               # 原本からそのまま抽出された事実の比率
  inferred: 0.10                                                # LLMが合成・推論した情報の比率
  inferred_by: "Librarian Agent v1.0"

# 信頼のライフサイクル（時間的失効）とシステム制御
status: "unreviewed"                                           # [unreviewed / reviewed]Reviewed化でwiki/へ自動昇格 [377, 402]
created: "2026-08-11T19:10:56"                                  # インジェスト日時
stale_after: "2026-11-11"                                      # ナレッジの賞味期限（3ヶ月） [377, 402]
tags: [project-A, mechanical, raw_ingest]
---
```

---

## 3. 「reviewed 判定」と昇格・原本退避の厳密フロー (MVP)

人間が `staging/` のノートを編集してステータスを `status: reviewed` に更新した際の、昇格プロキシ（`promoter.py`）の動作挙動を決定論的に定義する。

### ① 監視対象の厳密な限定
昇格プロキシは、`staging/**/*.md` ファイルのイベントのみを監視する。`staging/` 配下の `assets/` や画像ファイル（PNG等）、メタデータJSON（JSON）の変更イベントはすべて無視し、無駄なファイルオープンやVRAM競合を防止する。

### ② status 更新の検知方法とデバウンス制御
人間がエディタ（Obsidian等）で保存した際、ファイルの書き込みロックが解除されるまで安全に待機し、部分的な読み込みを防ぐための**「1秒間のデバウンス（Debounce）窓」**を設ける。
1.  `watchdog` の `on_modified` イベント、あるいは定期ファイル走査で対象 Markdown を検知。
2.  そのファイルの最終更新日時が現在時刻より1秒以上経過している（＝エディタの保存が完全に完了している）場合のみ、ファイルをオープンする。
3.  ファイルの先頭の YAML フロントマター（`---` で囲まれた最初のブロック）をスキャンし、`status:` フィールドの文字列を取得。
4.  文字列が `reviewed` (大文字小文字を区別しない、前後の空白は除去) である場合のみ、昇格トリガーを引く。

### ③ 一度昇格したファイルを再度処理しない制御（自己完結性）
昇格が発生した際、Markdownファイルと対応するアセットフォルダを `staging/` から `wiki/` へ物理的に**「移動 (os.rename / shutil.move)」**する。
*   これにより、処理対象のMarkdownファイルは `staging/` から物理的に消滅するため、二重パースや同じファイルを再度昇格処理する無限ループはファイルシステムレベルで完全に防止される。

### ④ 既に wiki/ に同名ファイルが存在する場合の競合対策
人間が過去に同名ノートをレビュー済みであったり、手動で同名ノートを配置していた場合の衝突を安全に防ぐため、**「非破壊退避バックアップルール」**を強制する。
1.  昇格先に同名ファイル（例: `wiki/project-A/sub/slug.md`）が既に存在する場合、その既存ファイルを `wiki/project-A/sub/slug.md.202608121945.bak` （タイムスタンプサフィックス付与）として物理的に名前変更して退避する。
2.  既存のアセットフォルダ（`wiki/project-A/sub/assets/slug/`）が存在する場合も、同様にタイムスタンプ付きのバックアップフォルダ（`wiki/project-A/sub/assets/slug.202608121945.bak/`）へ移動する。
3.  バックアップ確保が完了した後、新しいMarkdownおよびアセットフォルダを `wiki/` の該当箇所へ移動して配置する。これにより、人間が過去に加筆したWiki記述がサイロ化やサイレント上書きで失われるリスクを完全にゼロにする。

---

## 4. 再実行時の冪等性（Idempotency）＆重複回避ルール (MVP)

原本ファイルが `_raw/` へ再度投入されたり、デーモンが不慮の再起動等で再パース処理を行う際の、データの整合性保持ルール。

### ① インジェスト冪等性（原本の多重投入時の挙動）
原本ファイル（例: `doc.pdf` ⮕ スラッグ: `doc`）が `_raw/` ディレクトリに検知された際、デーモンはパースを開始する前に以下の検証を順に実行する。

*   **条件1: `wiki/` 配下に既に `{Slug名}.md`（status: reviewed）が存在する場合**
    *   **挙動**: **処理を完全にスキップする**。
    *   **理由**: `wiki/` にあるノートは、すでに人間が内容を確認して承認し、Obsidian等で美しく加筆編集している「本物の知識」である。自動パースでこれを上書きすると、人間のキュレーションがすべて破壊されるため、絶対に上書きしてはならない。
    *   **ログ出力**: `[SKIP] project-a_sub_doc already exists in wiki/ (status: reviewed). Ingest bypassed to protect human edits.`
*   **条件2: `staging/` 配下にのみ `{Slug名}.md`（status: unreviewed）が存在する場合**
    *   **挙動**: **安全に上書き（Overwrite）する**。
    *   **理由**: まだ人間に承認されていない下書き段階（Draft）であるため、原本の更新版として最新のパース結果で置き換えて差し支えない。

### ② アセットフォルダのクリーンアップルール
Doclingが原本を再パースして `staging/{DPI構造}/assets/{Slug名}/` 配下に新しいPNG画像を切り出す際、既存の古い画像ファイルが残ったままになると、PDFのページ削除等が発生していた場合に「ゴースト（孤立した古い画像）」がアセットフォルダ内に残留し、ゴミが蓄積される原因となる。
*   **ルール**: デーモンは画像を書き出す前に、対象の `assets/{Slug名}/` ディレクトリが存在する場合、**中身 of ファイル群をディレクトリごと一度物理削除（shutil.rmtree）し、空のフォルダを再作成してから新規画像を書き込む**。
*   これにより、アセットフォルダ内は常に「最新の原本ドキュメントの画像のみ」が100%の整合性で格納された状態が保証される。

---

## 5. 【層B】画像ファイル内部埋め込み（PNG tEXt Chunk：不変メタデータ）

Pillowを用いて、Doclingが切り出したPNG画像のバイナリ内部（tEXt チャンク領域）にメタデータを焼き込む。画像アセット単体がフォルダ外に孤立したり誤リネームされても、バイナリ自体からルーツと親ノートを決定論的に逆引き（Provenance of確保）可能にする。

### ① 埋め込みスキーマ（JSON）
*   **書き込みキー**: `llm_wiki_meta`
*   **ペイロード構造**:
```json
{
  "uuid": "img_project-A_sub-component_DWG-2026-X88_crop01",
  "parent_doc_id": "project-a_sub-component_dwg-2026-x88",
  "original_source": "raw_sources/project-A/sub-component/DWG-2026-X88.pdf",
  "page_number": 12,
  "bounding_box": [100, 150, 800, 600],
  "extracted_by": "Docling Engine v2.0",
  "extracted_at": "2026-08-11T19:10:56Z"
}
```

---

## 6. Markdown内における「画像アセット表現規約」

生成されるMarkdown本文内において、画像アセットを表示する際は、Obsidian等での美しさとキーワード検索性を両立させるため、以下の**「コールアウト付き画像リンク」**を自動付与して挿入する。

```markdown
![[assets/project-a_sub-component_dwg-2026-x88/fig1.png]]
> [!info] 📊 AI図表解説 (fig1.png)
> **対象**: [図表の種類（例: CAD構成図、上昇トレンド折れ線グラフ等）]
> **AI解釈**: [VLMによる詳細な画像解説（※MVP段階では「VLM解釈待機中」とプレースホルダー挿入）]
```

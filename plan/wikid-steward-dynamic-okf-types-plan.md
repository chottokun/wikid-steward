# wikid-steward: Raw Markdown 解析 ＆ 動的 OKF Type 定義・構造化コンパイル実装計画書 (v8.0)

本計画書は、`wikid-steward` において固定的な型（Concept のみ）に依存せず、**「生Markdown（`_raw/`）の抽出・解析を起点として、業務やドメインに応じた最適な OKF `type`（知識スキーマ）を動的に定義・拡張し、多面的な Wiki ノート群を結晶化させる」** ための次期開発計画である。

---

## 1. 背景と基本方針

### 1.1 現状の課題
* OKF v0.2 の規格は `Concept`, `Architecture Decision`, `Data Model`, `Runbook`, `Configuration` など多面的なナレッジ種別を許容しているが、現状の自動コンパイル処理は一律に `Concept` として切り出している。
* 業務ドキュメント（製造図面、品質標準、法務特許、医療プロトコル等）は分野ごとに固有の知識構造を持っており、単一の型定義では表現しきれない。

### 1.2 コア思想：2段階の知識結晶化サイクル (Fact -> Schema -> Wiki)
1. **Phase 1（事実の確定）**: 原本ドキュメントから忠実な生Markdownを抽出し、`_raw/{slug}.md` としてスナップショット保存する。
2. **Phase 2（型の発見・定義）**: 抽出された Raw Markdown 群を解析し、人間と AI が協調してそのドキュメント群に必要な知識型を `types.yaml` として定義する。
3. **Phase 3（構造化Wikiの生成）**: 定義された `type` に基づき、最適な見出し構造・必須セクション・ディレクトリ配置を持つ OKF v0.2 ノート群を自律コンパイルする。

---

## 2. システムアーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: 生Markdownの抽出・確定 (Extraction)               │
│  原本ファイル ➔ `_raw/{slug}.md` (OKF YAML付き生Markdown)    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: Raw Markdown 解析 ＆ 型定義 (Profiling & Schema)  │
│  ・`wikid-steward analyze-raw _raw/`                        │
│  ・ドキュメント群の構造・頻出パターンを LLM がプロファイリング │
│  ・人間による `types.yaml` の確定・カスタマイズ (Human-in-the-Loop)│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: スキーマ駆動 Wiki コンパイル (Schema-Driven Compile)│
│  ・`types.yaml` に基づくセマンティック自動型分類              │
│  ・型別テンプレートによるセクション自動生成                  │
│  ・自動ルーティング:                                         │
│      type: Concept               ➔ `wiki/concepts/`         │
│      type: Architecture Decision ➔ `wiki/architecture/`     │
│      type: Data Model            ➔ `wiki/data_models/`      │
│      type: Runbook               ➔ `wiki/runbooks/`         │
│  ・`[[WikiLink]]` 相互結合 ＆ MOC (index.md) 自動編成       │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. `types.yaml` スキーマ仕様

リポジトリルートまたは `profiles/` 配下に配置する型定義ファイル仕様：

```yaml
types:
  - name: "Concept"
    description: "専門用語、基礎理論、コア概念、アルゴリズム"
    required_sections:
      - "## 概要"
      - "## 別名・表記揺れ"
      - "## 📝 手書きメモ"
    tags: ["concept", "core"]
    routing_dir: "wiki/concepts"

  - name: "Architecture Decision"
    description: "アーキテクチャ上の意思決定、ADR、技術選定、トレードオフ"
    required_sections:
      - "## 背景 (Context)"
      - "## 意思決定 (Decision)"
      - "## 影響と結果 (Consequences)"
      - "## 📝 手書きメモ"
    tags: ["architecture", "adr"]
    routing_dir: "wiki/architecture"

  - name: "Data Model"
    description: "データ構造、データベーススキーマ、DTO、APIペイロード、部品表(BOM)"
    required_sections:
      - "## データ構造・スキーマ定義"
      - "## フィールド詳細 (Field Specifications)"
      - "## 📝 手書きメモ"
    tags: ["data", "schema"]
    routing_dir: "wiki/data_models"

  - name: "Runbook"
    description: "運用手順書、セットアップ手順、デプロイプロシージャ、障害対応手順"
    required_sections:
      - "## 前提条件 (Prerequisites)"
      - "## 実行手順 (Procedure Steps)"
      - "## トラブルシューティング (Troubleshooting)"
      - "## 📝 手書きメモ"
    tags: ["runbook", "operations"]
    routing_dir: "wiki/runbooks"

  - name: "Configuration"
    description: "設定値、環境変数仕様、システムパラメータ定義"
    required_sections:
      - "## 設定パラメータ一覧 (Parameters)"
      - "## 環境変数・認証情報 (Environment Variables)"
      - "## 📝 手書きメモ"
    tags: ["config", "infrastructure"]
    routing_dir: "wiki/configs"
```

---

## 4. コア機能の実装ステップ

### Step 1: Raw Markdown プロファイリング コマンドの実装
* **新コマンド**: `wikid-steward profile-raw [dir]`
* **機能**:
  * `_raw/` 配下の Markdown 群をスキャンし、頻出する知識パターン（手順、データ構造、設計判断、概念等）を LLM で要約分析。
  * 推奨される `types.yaml` のドラフトを自動生成し、人間に提示。

### Step 2: 多面的トピック分類 ＆ 型別テンプレートエンジンの実装
* **`TopicClassifier`**:
  * `GlossaryExtractor` を `SemanticTopicExtractor` へ拡張。
  * 各トピックについて `title`, `type` (`types.yaml` から選択), `description`, `key_points` を一括抽出。
* **`TypeTemplateRenderer`**:
  * `required_sections` に応じた見出し構造を自動生成。
  * 手書きメモ領域（`## 📝 手書きメモ`）を全ノートに標準配置。

### Step 3: ディレクトリ自動ルーティング ＆ MOC 連携
* 抽出された `type` の `routing_dir`（例: `wiki/architecture/`）に従って各ファイルを自動配置。
* `wikid-steward moc` と連動し、型別・カテゴリ別の目次インデックス（`README.md` / `index.md`）を自動再編。

### Step 4: ヒトによる査読・型確定 (Human-in-the-Loop)
* `wikid-steward review <file> [--type <new_type>]`
* 人間が `type` を変更した場合、自動で適切なルーティング先フォルダへ移動させ、フロントマターと MOC を更新。

---

## 5. 検証計画

1. **スキーマロード互換性テスト**:
   * `types.yaml` が存在しない場合でもデフォルト 5 種別で 100% 正常動作することの検証。
2. **多面的分類テスト**:
   * ADR 文書、手順書、データ構造定義を含む Markdown から、それぞれ `Architecture Decision`, `Runbook`, `Data Model` が正しく分類・生成されることを検証。
3. **手書きメモ ＆ 既存ノート保護テスト**:
   * どの `type` のノートであっても、手書きメモ保護ガードレールと言及ソース追記が正しく機能することを検証。

# Knowledge Update Log

## 2026-08-17

* **Creation**: 様々なドキュメントを OKF v0.2 思想に準拠した Markdown 群（生Markdown、メインノート、1トピック=1ファイルの概念・用語ノート群）にコンパイルする `DocumentToOKFCompiler` (`src/wikid_steward/core/document_compiler.py`) を実装。
* **Update**: CLI `wikid-steward compile` コマンドを刷新し、ファイル・ディレクトリ指定、`--status` (draft/stable)、`--auto-stable`、`--reviewer`、原本バイナリ保存選択 (`--save-source/--no-save-source`)、原本リンク露出制御 (`--hide-source-links`)、用語抽出・分解 (`--extract-terms`) をサポート。
* **Update**: `_raw/{slug}.md` への生Markdown出力時にも OKF v0.2 YAML フロントマター、画像アセット埋め込み、手書きメモ保護領域を完全適用するベストプラクティス化を実施。

## 2026-08-15

* **Creation**: v7.0 拡張仕様として、バックリンク集約 ＆ 用語定義自動逆合成仕様 ([`docs/architecture/retro_compiler.md`](./architecture/retro_compiler.md)) を追加。
* **Creation**: 手書きメモ保護 ＆ ガードレール仕様 ([`docs/architecture/human_memo.md`](./architecture/human_memo.md)) を追加。
* **Creation**: 外部DB不要の軽量メタデータ ＆ 1-Hop グラフ巡回検索仕様 ([`docs/architecture/graph_search.md`](./architecture/graph_search.md)) を追加。
* **Update**: ナレッジ健全性監査仕様 ([`docs/architecture/linter.md`](./architecture/linter.md)) を更新し、赤リンクのスタブ隔離起票 (`wiki/stubs/`)、タイポサジェスト（安全警告のみ）、脚注静的整合性スキャンを反映。
* **Update**: 用語自動抽出 ＆ WikiLink バインディング仕様 ([`docs/domain/relinker_glossary.md`](./domain/relinker_glossary.md)) を更新し、多層トークナイズ保護、セクション別ファーストヒット置換、GFM相互変換を反映。
* **Update**: ナレッジ・ライフサイクル仕様 ([`docs/domain/lifecycle.md`](./domain/lifecycle.md)) を更新し、スタブ隔離と二段階昇格ライフサイクル、および Git ブランチ & PR 協調モデル (`steward/auto-compiler` ＋ `[skip ci]`) を反映。
* **Update**: ハイブリッド検索仕様 ([`docs/infrastructure/vector_search.md`](./infrastructure/vector_search.md)) を更新し、超軽量ファイルベース検索エンジン (v7.0) を反映。
* **Update**: 各種インデックス ([`docs/index.md`](./index.md), [`docs/architecture/index.md`](./architecture/index.md)) を最新化。

## 2026-08-14

* **Creation**: インフラ領域ナレッジ [`docs/infrastructure/`](./infrastructure/index.md) を新設し、リアルタイム監視・自動昇格デーモン ([`daemon.md`](./infrastructure/daemon.md)) および Qdrant ベクトル検索 ＆ 1-Hop WikiLink グラフ巡回仕様 ([`vector_search.md`](./infrastructure/vector_search.md)) を追加。
* **Creation**: アーキテクチャ領域に動的 MOC 生成仕様 ([`docs/architecture/moc.md`](./architecture/moc.md)) およびナレッジ健全性 Linter 仕様 ([`docs/architecture/linter.md`](./architecture/linter.md)) を追加。
* **Creation**: ドメイン領域に用語自動抽出 ＆ WikiLink バインディング仕様 ([`docs/domain/relinker_glossary.md`](./domain/relinker_glossary.md)) を追加。
* **Update**: [`docs/index.md`](./index.md), [`docs/architecture/index.md`](./architecture/index.md), [`docs/domain/index.md`](./domain/index.md) の目次インデックスを最新の実装と完全同期。

## 2026-08-12

* **Creation**: LLM-Wiki (OKF) ナレッジベースを初期化しました。
* **Ingestion**: `plan/` 配下の v5 実装計画（ライフサイクル、スラッグ生成、Docling統合、2層メタデータ仕様）をドキュメントナレッジとして反映。
* **Documentation**: カスタムプロファイルハンドラー作成手順およびコードテンプレート (`docs/architecture/handlers.md`) を拡充・同期。

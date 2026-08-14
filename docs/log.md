# Knowledge Update Log

## 2026-08-14

* **Creation**: インフラ領域ナレッジ [`docs/infrastructure/`](./infrastructure/index.md) を新設し、リアルタイム監視・自動昇格デーモン ([`daemon.md`](./infrastructure/daemon.md)) および Qdrant ベクトル検索 ＆ 1-Hop WikiLink グラフ巡回仕様 ([`vector_search.md`](./infrastructure/vector_search.md)) を追加。
* **Creation**: アーキテクチャ領域に動的 MOC 生成仕様 ([`docs/architecture/moc.md`](./architecture/moc.md)) およびナレッジ健全性 Linter 仕様 ([`docs/architecture/linter.md`](./architecture/linter.md)) を追加。
* **Creation**: ドメイン領域に用語自動抽出 ＆ WikiLink バインディング仕様 ([`docs/domain/relinker_glossary.md`](./domain/relinker_glossary.md)) を追加。
* **Update**: [`docs/index.md`](./index.md), [`docs/architecture/index.md`](./architecture/index.md), [`docs/domain/index.md`](./domain/index.md) の目次インデックスを最新の実装と完全同期。

## 2026-08-12

* **Creation**: LLM-Wiki (OKF) ナレッジベースを初期化しました。
* **Ingestion**: `plan/` 配下の v5 実装計画（ライフサイクル、スラッグ生成、Docling統合、2層メタデータ仕様）をドキュメントナレッジとして反映。
* **Documentation**: カスタムプロファイルハンドラー作成手順およびコードテンプレート (`docs/architecture/handlers.md`) を拡充・同期。

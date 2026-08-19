# 開発計画書・設計書インデックス (Plans & Specifications)

`plan/` ディレクトリは、`wikid-steward` のシステム設計、機能追加、リファクタリング等の実装計画書（Plan）および詳細設計仕様書を管理する領域です。

---

## 🚀 進行中の計画 (Active Plans)

現在開発中または実装検討中のアクティブな計画書です。

| ドキュメント | 対象バージョン / 領域 | 概要 |
| :--- | :--- | :--- |
| [**wikid-steward-dynamic-okf-types-plan.md**](./wikid-steward-dynamic-okf-types-plan.md) | **v8.0** / コア機能 | Raw Markdown 解析 ＆ 動的 OKF Type 定義・構造化コンパイル実装計画書。ドメインに応じた柔軟な OKF `type` の自動プロファイリングと生成。 |
| [**llm-resilience-and-timeout-recovery-plan.md**](./llm-resilience-and-timeout-recovery-plan.md) | 共通 / 堅牢化 | LLM 推論堅牢化・タイムアウト回復・処理性能最適化計画。タイムアウト時のフォールバックおよび最小テキスト長判定ガード。 |

---

## 🗄️ アーカイブ済み計画 (Archived Plans)

すでに実装・リリースが完了した計画書、および旧アーキテクチャの履歴ドキュメントです。詳細は [`archive/`](./archive/) ディレクトリを参照してください。

### v7.0 完了分 (軽量 CLI ＋ GFM ＋ SimpleWiki 統合)
* [**wikid-steward-minimal-integration-plan-v7.md**](./archive/wikid-steward-minimal-integration-plan-v7.md): Qdrant 依存を排除し、プレーン GFM Markdown ＋ Git ＋ 軽量 CLI による自律協調システムへの刷新計画書。
* [**wikid-steward-wikilink-design-v7.md**](./archive/wikid-steward-wikilink-design-v7.md): `[[WikiLink]]` 処理、セルフヒーリング、`<!-- HUMAN BEGIN -->` ガードレール、およびスタブ逆合成の詳細設計書。
* [**wikid-steward-implementation-checklist.md**](./archive/wikid-steward-implementation-checklist.md): v7.0 コア機能・LLM 連携・ブランチ戦略の実装＆実証チェックリスト（全項目完了済み）。

### v5.0 / Phase 3 (初期リブート・Docling 検討期)
* [**llm-wiki-simple-reboot-plan-v5.md**](./archive/llm-wiki-simple-reboot-plan-v5.md): v5.0 システムリブート計画。
* [**llm-wiki-reboot-docling-spec-v5.md**](./archive/llm-wiki-reboot-docling-spec-v5.md): Docling パース仕様書。
* [**llm-wiki-reboot-metadata-spec-v5.md**](./archive/llm-wiki-reboot-metadata-spec-v5.md): OKF v0.2 メタデータ設計書。
* [**phase3_critical_analysis_and_countermeasures.md**](./archive/phase3_critical_analysis_and_countermeasures.md): Phase 3 批判的分析と対策。
* [**phase3_llm_wiki_expansion.md**](./archive/phase3_llm_wiki_expansion.md): Phase 3 拡張計画。

### v2.5 (旧 Qdrant / メダリオン構造期)
* [**wikid_steward_implementation_plan_v2_5.md**](./archive/wikid_steward_implementation_plan_v2_5.md): Qdrant ベクトル DB および 3層メダリオン構造を前提とした初期実装計画書。

---

## 📌 運用ルール

1. **新規計画の作成**: 新機能や大幅な仕様変更を計画する際は、本ディレクトリ（`plan/`）直下に計画書を作成し、本 `README.md` の「進行中の計画」に追記してください。
2. **完了時のアーカイブ**: 計画が完了・マージされたドキュメント、または方針転換により過去のものとなったドキュメントは `archive/` ディレクトリに移動し、本 `README.md` を更新してください。
3. **原本ドキュメントとの分離**: 入力用ドキュメントやテスト用原本は `_raw/` や `docs/raw/` に配置し、本ディレクトリにはシステム開発計画のみを配置してください。

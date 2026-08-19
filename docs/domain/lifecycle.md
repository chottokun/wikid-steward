---
type: "Data Model"
title: "ナレッジ・ライフサイクル ＆ メダリオン 3 層運用仕様 (v7.0)"
sources:
  - resource: "/plan/wikid_steward_implementation_plan_v2_5.md"
  - resource: "/src/wikid_steward/core/promoter.py"
  - resource: "/src/wikid_steward/core/retro_compiler.py"
  - resource: "/src/wikid_steward/core/human_memo.py"
  - resource: "/src/wikid_steward/vector/indexer.py"
status: "stable"
generated:
  by: "agent/antigravity"
  at: "2026-08-19T21:44:00Z"
description: "メダリオン 3 層構造 (Bronze/Silver/Gold)、Silver層止め (Early Stopping)、スタブ隔離・二段階昇格、手書きメモ保護、ガベージコレクション運用仕様"
tags:
  - "lifecycle"
  - "medallion"
  - "early-stopping"
  - "stubs"
  - "promotion"
  - "garbage-collection"
  - "hitl"
---

# ナレッジ・ライフサイクル ＆ メダリオン 3 層運用仕様 (v7.0)

`wikid-steward` は、原本バイナリの非構造化データから洗練された概念ネットワークに至るまでを **メダリオン・アーキテクチャ（Bronze / Silver / Gold）** に沿って管理し、人間による手書きメモの絶対保護と自動ガベージコレクションを提供します。

---

## 1. メダリオン 3 層構造とパイプライン

```
  [Bronze層: _raw/] ──(決定論的パース)──▶ [Silver層: wiki/raw_markdown/] ──▶ 【ユーザー閲覧・直接利用】
                                                   │
                                                   │ (明示的指示 OR バックリンク蓄積)
                                                   ▼
                                        [Gold層: wiki/concepts/]
```

### 1.1 Bronze 層（生データ領域: `_raw/`）
* PDF、DOCX、PPTX、XLSX、ソースコード等の原本バイナリおよび投入テキストが配置される領域。

### 1.2 Silver 層（Staging 領域: `wiki/raw_markdown/`）
* `_raw/` のデータを決定論的にパース（Docling 等）し、必須 OKF v0.2 メタデータ（`type: RawSource`, `title`, `source_path` 等）を付与した標準 Markdown 領域。
* **Silver 層での止め (Early Stopping)**:
  すべてのドキュメントを LLM で Gold 層へ要約・昇華する必要はありません。日常的な議事録や調査レポートは Silver 層のままナレッジとして安全に閲覧・検索利用できます。

### 1.3 Gold 層（Knowledge 領域: `wiki/concepts/`, `wiki/glossary/`）
* LLM エージェント（`retro_compiler.py` / `promoter.py`）が重要な概念を用約・昇華させた高品質ナレッジ領域。
* バックリンク蓄積数（デフォルト: 3件以上）や明示的コマンド実行によって生成されます。

---

## 2. スタブ隔離と二段階昇格ライフサイクル

未完成な AI 下書きによる本番 Vault の汚染を防ぐため、未定義用語は専用フォルダに隔離起票されます。

```text
[ リンク切れ検知 ] ──▶ [ 隔離: wiki/stubs/{slug}.md ] (status: draft)
                                  │
          ┌───────────────────────┴───────────────────────┐
          ▼                                               ▼
[ 自動逆合成 (Retro-Compiler) ]                     [ 人間による査読承認 (Review) ]
(被リンク >= 3件で文脈から自動生成)                (wikid-steward review コマンド)
          │                                               │
          └───────────────────────┬───────────────────────┘
                                  ▼
                    [ 本番昇格: wiki/concepts/ ] (status: stable)
```

---

## 3. 人間手書きメモの絶対保護 (Guarded Merge)

AI エージェントが概念ノートの再コンパイルや重複マージを行う際、ノート内の手書きメモは 100% 維持されます。

```markdown
---
title: PID Controller
type: Concept
---

# PID Controller
AI が生成した最新の概念解説文...

<!-- HUMAN BEGIN -->
### 現場チューニングメモ (極秘)
* Kd ゲインは 0.05 を超えると高周波ノイズでハンチングを起こす
* 冬場はオイル粘度低下のため Kp を +10% 増やす
<!-- HUMAN END -->

## Reference Links
* [[Motor Control]]
```

* `merge_human_memo` ロジックにより、`<!-- HUMAN BEGIN -->` 〜 `<!-- HUMAN END -->` のブロックは AI の再生成処理によって上書き・削除されることは一切ありません。

---

## 4. 物理削除と自律ガベージコレクション (GC)

* **ユーザー直接削除の受容**:
  ユーザーが Obsidian や VSCode 等で Markdown ファイルを直接物理削除した場合でも、システムは破綻しません。
* **Qdrant 孤立 Point のパージ**:
  次回 `wikid-steward index` 実行時にディスクと Qdrant コレクションが照合され、削除されたファイルに対応する Point が自動的にパージ（`prune_deleted_points`）されます。
* **リンク切れの自動修復**:
  削除によって発生したリンク切れは、`wikid-steward lint` によって検知され、必要に応じて `wiki/stubs/` に自動スタブが起票されます。

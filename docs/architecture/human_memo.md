---
type: "Architecture Decision"
title: "手書きメモ保護 ＆ ガードレール仕様 (v7.0)"
sources:
  - resource: "/src/wikid_steward/core/human_memo.py"
status: "stable"
generated:
  by: "agent/antigravity"
  at: "2026-08-15T00:05:00Z"
description: "<!-- HUMAN BEGIN --> ... <!-- HUMAN END --> タグによる人間編集メモの退避・保護・マージ機構の仕様"
tags:
  - "human-memo"
  - "guardrails"
  - "safety"
  - "merge"
---

# 手書きメモ保護 ＆ ガードレール仕様 (`core/human_memo.py`)

AI による自律コンパイル、逆合成、Relink 等の自動更新処理において、人間がノート内に記述した現場メモ・特記事項が上書き・破壊されるのを防ぐ二重防壁機構。

## 構造とタグ規約

各 Markdown ノートの末尾に以下のセクションを配置：

```markdown
## 📝 手書きメモ

<!-- HUMAN BEGIN -->
現場検証メモ: Dゲインはノイズ耐性を考慮して小さめに設定すること。
<!-- HUMAN END -->
```

## 保護・マージアルゴリズム

1. **抽出 (`extract_human_memo`)**:
   - `<!--\s*HUMAN\s+BEGIN\s*-->([\s\S]*?)<!--\s*HUMAN\s+END\s*-->` 正規表現でタグ内の文字列を完全抽出。
2. **保護退避 (`strip_human_memo_for_protection`)**:
   - AI による再生成前に本文から手書きメモを一時退避。
3. **安全マージ (`merge_human_memo`)**:
   - AI の生成完了後、退避していたメモブロックを自動で末尾に再結合。
   - 人間のメモが1文字も欠損・改変されることなく維持されることを保証。

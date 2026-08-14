---
type: "Architecture Decision"
title: "ナレッジ健全性監査 ＆ セルフヒーリング仕様 (v7.0)"
sources:
  - resource: "/src/wikid_steward/core/linter.py"
status: "stable"
generated:
  by: "agent/antigravity"
  at: "2026-08-15T00:05:00Z"
description: "KnowledgeLinter によるスタブ自動起票、タイポサジェスト、脚注整合性、画像リンク切れ、OKF Frontmatter欠損の監査仕様"
tags:
  - "linter"
  - "integrity"
  - "self-healing"
  - "stubs"
  - "audit"
---

# ナレッジ健全性監査 ＆ セルフヒーリング仕様 (`core/linter.py`)

ナレッジベース（`wiki/`）の肥大化や手動編集に伴うリンク切れ、メタデータ欠損、孤立ノート（Orphan Note）、未解決赤リンク、脚注不整合を全自動検知・監査し、スタブ起票で自己修復を行う静的検証エンジン。

## 監査項目

1. **未解決赤リンク検知とスタブ自動隔離起票 (`UNRESOLVED_WIKILINK`)**:
   - `[[未定義用語]]` を検知した場合、本番ディレクトリ（`concepts/` 等）を汚さず、隔離ディレクトリ **`wiki/stubs/{slug}.md`** に OKF v0.2 形式（`status: draft`、手書きメモ枠付き）で自動起票。
2. **タイポ・表記揺れサジェスト (`TYPO_SUGGESTION`) [安全仕様]**:
   - カタカナ・ひらがな正規化およびレーベンシュタイン距離／SequenceMatcher による類似度（$\ge 0.75$）計算で既存ノートとの類似を警告表示。
   - **安全策**: 類似概念の意図しない統合・知識破損を防ぐため、**本文の自動書き換え・訂正は行わず警告のみを発行**。
3. **脚注・出典静的整合性スキャン (`MISSING_FOOTNOTE_SOURCE` / `ORPHAN_FOOTNOTE`)**:
   - 本文中の脚注 `[^id]` と Frontmatter の `sources[].id` の対応関係を監査。
4. **OKF Frontmatter 整合性 (`MISSING_FRONTMATTER`)**:
   - 先頭に YAML Frontmatter (`---`) が存在し、必須キー（`type`, `title`）が含まれているか検証。
5. **画像リンク切れ検知 (`BROKEN_IMAGE_LINK`)**:
   - `![alt](path)` 形式の相対画像パス（`assets/{slug}/figX.png` など）が実在するか検証。
6. **孤立ノート検知 (`ORPHAN_NOTE`)**:
   - 他のノートから一度もリンクされていない未接続ノートを検知。

## 実行インターフェース

```bash
# 監査およびスタブ自動起票
uv run wikid-steward lint

# 監査・タイポ警告のみ表示 (スタブ作成なし)
uv run wikid-steward lint --dry-run
```

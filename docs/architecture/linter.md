---
type: architecture
title: ナレッジ健全性監査 ＆ セルフヒーリング仕様
sources: src/wikid_steward/core/linter.py
status: stable
generated:
  by: agent/gemini-3.7-flash
  at: "2026-08-14T23:08:00+09:00"
description: KnowledgeLinter による画像リンク切れ、OKF Frontmatter欠損、孤立ノートの監査仕様
tags: [linter, integrity, self-healing, audit]
---

# ナレッジ健全性監査 ＆ セルフヒーリング仕様 (`core/linter.py`)

ナレッジベース（`wiki/`）の肥大化や手動編集に伴うリンク切れ、メタデータ欠損、孤立ノート（Orphan Note）を全自動検知・監査する静的検証エンジン。

## 監査項目

1. **OKF Frontmatter 整合性 (`MISSING_FRONTMATTER`)**:
   - 先頭に YAML Frontmatter (`---`) が存在するか。
   - 必須キー（`id`, `title`）が含まれ、正常にパース可能であるか。
2. **画像リンク切れ検知 (`BROKEN_IMAGE_LINK`)**:
   - `![alt](path)` 形式の相対画像パス（`assets/{slug}/figX.png` など）が実在するか検証。
3. **孤立ノート検知 (`ORPHAN_NOTE`)**:
   - 目次ファイル（`index.md`）および用語集（`glossary/`）を除き、他のノートから一度もリンクされていない未接続ノートを検知。

## 実行インターフェース

```bash
uv run wikid-steward lint
```

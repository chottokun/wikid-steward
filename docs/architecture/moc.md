---
type: architecture
title: 動的 MOC (Map of Content) 生成仕様
sources: src/wikid_steward/core/moc_generator.py
status: stable
generated:
  by: agent/gemini-3.7-flash
  at: "2026-08-14T23:08:00+09:00"
description: moc_generator によるカテゴリ別目次インデックス (index.md) の動的再編・自動生成仕様
tags: [moc, map-of-content, index, navigation]
---

# 動的 MOC (Map of Content) 生成仕様 (`core/moc_generator.py`)

ナレッジベース内の各サブディレクトリに対し、配下のドキュメント一覧・ドキュメント種別を解析して最新の目次マップノート（`index.md`）を自動生成・最新化するモジュール。

## 生成ロジック

1. ディレクトリ内のすべての Markdown ファイル（`index.md`, `*.bak` を除く）を走査。
2. 各ノートの YAML Frontmatter から `title` および `type` を抽出。
3. タイトル昇順でソートし、OKF 準拠の Frontmatter を付与した Markdown 目次ツリーを生成。

## 実行インターフェース

```bash
uv run wikid-steward moc
```

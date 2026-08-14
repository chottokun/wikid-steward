---
type: "Data Model"
title: "用語自動抽出 ＆ WikiLink バインディング仕様 (v7.0)"
sources:
  - resource: "/src/wikid_steward/core/glossary.py"
  - resource: "/src/wikid_steward/core/relinker.py"
status: "stable"
generated:
  by: "agent/antigravity"
  at: "2026-08-15T00:05:00Z"
description: "LLM による専門用語抽出と多層トークナイズ保護＋セクション別ファーストヒット置換＋GFM相互変換仕様"
tags:
  - "glossary"
  - "relinker"
  - "wikilink"
  - "gfm"
---

# 用語自動抽出 ＆ WikiLink バインディング仕様 (`core/relinker.py`, `core/glossary.py`)

`wikid-steward` は、ドキュメントのインジェストやコンパイル時に、重要概念・専門用語を LLM で自動検出し、用語ノートの作成および本文内の未リンク単語を `[[用語名]]` へ安全に相互結合するエンジンを備えています。

## 1. 用語自動抽出 (`GlossaryExtractor`)

- LLM (`gemma4:latest` 等) に対して技術文書から重要で専門性の高い概念（Key Terms / Concepts）の抽出を依頼。
- JSON 形式（`canonical_title`, `aliases`, `description`）で受け取り、`wiki/glossary/{slug}.md` に用語説明ノートを生成。
- 一般名詞（AI, model, file, data 等）の除外フィルタリングを実施。

## 2. 堅牢型 WikiLink バインダー (`WikiRelinker`)

手動・自動の相互リンク生成における「二重リンク `[[[[用語]]]]`」や「コードブロック内の誤置換」を完全に排除するため、多層トークナイズ保護アーキテクチャを採用。

### 保護対象トークン群
1. **Frontmatter (`---...---`)**
2. **手書きメモ全体 (`<!-- HUMAN BEGIN --> ... <!-- HUMAN END -->`)**
3. **コードブロック (````...````)**
4. **インラインコード (`` `...` ``)**
5. **数式ブロック (`$$...$$`, `$...$`)**
6. **HTML テーブル (`<table>...</table>`)**
7. **HTML コメント (`<!-- ... -->`)**
8. **画像リンク (`![...](...)`, `![[...]]`)**
9. **既存リンク (`[...](...)`, `[[...]]`)**
10. **Markdown 見出し行 (`# ...`)**

### 置換ポリシー
- **セクション別ファーストヒット置換 (`mode: "first_hit_per_section"`)**:
  大見出し（`##`）セクションごとに用語の初出 1 回のみリンク化。長い文書でもセクションごとに読みやすさを維持しつつ過剰リンクを防止。
- **マルチバイト単語境界対応**:
  日本語と英語が混在する文章でも英単語の途中置換を防ぐ境界判定。

## 3. GFM 相互変換 (`GFMConverter`)

Obsidian 形式の `[[WikiLink]]` と GitHub Flavored Markdown (GFM) 標準の相対パスリンク形式（`[表示名](/wiki/...)`）を相互変換する機能を提供し、GitHub Web UI や外部 Markdown ツールでの完全な可読性を担保します。

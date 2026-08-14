---
type: domain
title: 用語自動抽出 ＆ WikiLink バインディング仕様
sources:
  - src/wikid_steward/core/glossary.py
  - src/wikid_steward/core/relinker.py
status: stable
generated:
  by: agent/gemini-3.7-flash
  at: "2026-08-14T23:08:00+09:00"
description: LLM による専門用語抽出とセグメント保護＋1パス最長一致置換による安全な WikiLink 相互結合
tags: [glossary, relinker, wikilink, nlp]
---

# 用語自動抽出 ＆ WikiLink バインディング仕様

`wikid-steward` は、ドキュメントが公開（昇格）される際に、重要概念・専門用語を LLM で自動検出し、用語ノートの作成および本文内の未リンク単語を `[[用語名]]` へ相互リンク化するメカニズムを備えています。

## 1. 用語自動抽出 (`GlossaryExtractor`)

- LLM (`gemma4:latest` 等) に対して技術文書から重要で専門性の高い概念（Key Terms / Concepts）の抽出を依頼。
- JSON 形式（`canonical_title`, `aliases`, `description`）で受け取り、`wiki/glossary/{slug}.md` に用語説明ノートを生成。
- 一般名詞（AI, model, file, data 等）の除外フィルタリングを実施。

## 2. 堅牢型 WikiLink バインダー (`WikiRelinker`)

手動・自動の相互リンク生成における最大の課題である「二重リンク `[[[[用語]]]]`」や「コードブロック内の誤置換」を排除するため、セグメント分離型アプローチを採用。

### アルゴリズム
1. **保護領域の分離**:
   - コードブロック (````...````)、インラインコード (`` `...` ``)、数式ブロック (`$$...$$`, `$...$`)、既存画像リンク (`![...]`)、既存 WikiLink (`[[...]]`)、Markdown 見出し (`# ...`) を検知して置換対象から隔離。
2. **最長一致優先 (Longest Match First)**:
   - 表記揺れ・別名（aliases）を文字列長が長い順にソートして正規表現を構築。
3. **1パス置換 ＆ 初出限定**:
   - 同一ドキュメント内では用語ごとに初出 1 回のみ `[[用語名]]` に置換し、過剰リンク化を防止。

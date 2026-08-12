---
type: architecture
title: Docling パースパイプライン統合仕様
sources: plan/llm-wiki-reboot-docling-spec-v5.md
description: chottokun/docling-markdown-generator を Python Direct Import で呼び出し構造化パースを行う仕様
tags: [docling, parser, python, direct-import]
---

# Docling パースパイプライン統合仕様

`chottokun/docling-markdown-generator` (Docling v2.x ベース) を Python 直接ライブラリ参照 (Direct Import) 形式で呼び出す。

## パイプライン設定仕様

```python
# 設定パラメータ仕様
do_ocr = False                          # デジタルPDFのハルシネーション防止
do_table_structure = True               # 高精度テーブル認識
table_structure_options.mode = "accurate" # セル結合を維持した HTML <table> 出力
images_scale = 2.0                      # 画像解像度スケール
generate_picture_images = True          # 図表の抽出
generate_picture_descriptions = False   # MVPでは VLM 呼び出しを一時バイパス
```

## 画像リンク置換とアセット配置
* Markdown 出力内の画像リンクを一律 `assets/{Slug名}/{画像名}.png` (深さ1の相対パス) に置換。
* アセット書き出し前に `assets/{Slug名}/` が存在する場合は `shutil.rmtree` で一律クリアし、古い世代の切り出し画像（ゴーストファイル）を追放（冪等性確保）。

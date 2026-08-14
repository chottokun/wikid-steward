---
type: architecture
title: 2層ハイブリッドメタデータ設計 (層A + 層B)
sources: plan/llm-wiki-reboot-metadata-spec-v5.md
description: Markdown 可変メタデータ (層A) と PNG tEXt 不変バイナリメタデータ (層B) の二重化仕様
tags: [metadata, yaml, png-text, pillow]
---

# 2層ハイブリッドメタデータ設計

ポータビリティとトレーサビリティを両立するため、メタデータを2層で管理する。

## 1. 【層A】Markdown YAML Frontmatter (可変メタデータ)
人間が Obsidian 等で閲覧・編集可能であり、プロキシのステータス監視 (`status`) に利用。
* `id`, `title`, `type` (OKF必須), `path`, `source`, `provenance`, `status`, `created`, `stale_after`, `tags`

## 2. 【層B】PNG tEXt チャンク (不変バイナリメタデータ)
Pillow を用いて切り出し画像の中に直接書き込む不変メタデータ。
* キー名: `llm_wiki_meta`
* ペイロード: `uuid`, `parent_doc_id`, `original_source`, `page_number`, `bounding_box`, `extracted_by`, `extracted_at`

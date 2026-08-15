---
type: "Architecture Decision"
title: "バックリンク集約 ＆ 用語定義自動逆合成仕様 (v7.0)"
sources:
  - resource: "/src/wikid_steward/core/retro_compiler.py"
status: "stable"
generated:
  by: "agent/antigravity"
  at: "2026-08-15T00:05:00Z"
description: "未定義スタブに対するバックリンク文脈集約、AI循環汚染防止、LLM定義逆合成、および二段階昇格ライフサイクルのアーキテクチャ仕様"
tags:
  - "retro-compiler"
  - "backlinks"
  - "hallucination-prevention"
  - "stubs"
---

# バックリンク集約 ＆ 用語定義自動逆合成仕様 (`core/retro_compiler.py`)

孤立したスタブ（`wiki/stubs/`）に対して、組織内の複数のドキュメントからリンクされた文脈情報を集約し、LLM が組織固有の定義・解説レジュメを後追いで自動逆合成（Retro-Compilation）するエンジン。

## 主要メカニズム

### 1. 被リンク重複排除 ＆ スニペット集約
- 各ドキュメントからの被リンクをスキャンし、同一ドキュメントからの複数リンクは1件として重複排除。
- リンク周辺の文脈スニペット（段落・文章）を有向グラフから抽出。

### 2. AI 循環コピー汚染遮断フィルター (Anti-Hallucination Guard)
- 文脈集約時、`status: draft` かつ AI 生成物（未査読）のノートはスキャン対象から **100% 排除**。
- 人間が作成・査読済みの信頼できるノート（`status: stable` または `human:*`）のみを定義生成の文脈として採用し、AI の誤情報・ハルシネーションの自己増殖を防止。

### 3. 用語定義レジュメの逆合成 ＆ 手書きメモ保護マージ
- 被リンク数が閾値 $N$（デフォルト: 3 件）に達した用語、または手動強制実行（`--force`）時に、LLM が概要・動作原理・使われ方・注意点をまとめた Markdown を生成。
- 既存のスタブに含まれる「## 📝 手書きメモ」（`<!-- HUMAN BEGIN --> ... <!-- HUMAN END -->`）を抽出・保護し、生成結果の末尾に完全マージ。

### 4. 二段階昇格（スタブから本番 concepts/ へ移動）
- 逆合成が完了したノートは、`wiki/stubs/{slug}.md` から本番フォルダ **`wiki/concepts/{slug}.md`** へ自動移動。
- フロントマターの `status` を `stable` に昇格、`generated.by` を `wikid-steward/auto-compiler` に更新。

## 実行インターフェース

```bash
# 特定用語の逆合成
uv run wikid-steward compile-stub "PID制御"

# 閾値未満でも強制逆合成
uv run wikid-steward compile-stub "PID制御" --force

# 全スタブの一括逆合成
uv run wikid-steward compile
```

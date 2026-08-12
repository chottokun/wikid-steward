---
type: domain
title: 4層ナレッジライフサイクル
sources: plan/llm-wiki-simple-reboot-plan-v5.md
description: _raw/, staging/, wiki/, raw_sources/ の4層間をファイルシステム上で物理移動するライフサイクルモデル
tags: [lifecycle, staging, wiki, hitl]
---

# 4層ナレッジ・ライフサイクル仕様

原本バイナリの肥大化による Git リポジトリの破綻を防ぎ、人間介在型レビュー (HITL) を安全に回すため、ナレッジのフェーズを4つの階層に定義する。

## ライフサイクル遷移

```text
[ 投入: _raw/ ] ──(watchdog & Doclingパース)──> [ 検証: staging/ ]
                                                       │
                                          (status: reviewed 変更)
                                                       ▼
[ 退避: raw_sources/ ] <──(原本退避)───────── [ 公開: wiki/ ]
```

1. **投入フェーズ (`_raw/`)**: 原本バイナリ（PDF/DOCX/PPTX/XLSX等）を投入。
2. **検証フェーズ (`staging/`)**: 未審査ノート (`status: unreviewed`) と画像アセットが配置され、Obsidian 等でレビューを待機。
3. **公開フェーズ (`wiki/`)**: 承認されたノート (`status: reviewed`) が物理移動 (`shutil.move`) され、Git 管理下で公開・RAG登録。
4. **退避フェーズ (`raw_sources/`)**: 昇格と同時に原本バイナリが Git 管理外の外部アーカイブに物理移動。

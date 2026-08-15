---
type: "Data Model"
title: "ナレッジ・ライフサイクル ＆ 二段階昇格仕様 (v7.0)"
sources:
  - resource: "/plan/wikid-steward-minimal-integration-plan-v7.md"
  - resource: "/src/wikid_steward/core/promoter.py"
  - resource: "/src/wikid_steward/core/retro_compiler.py"
status: "stable"
generated:
  by: "agent/antigravity"
  at: "2026-08-15T00:05:00Z"
description: "_raw/, staging/, wiki/stubs/, wiki/concepts/, raw_sources/ の5層ライフサイクルとGit PR協調モデル"
tags:
  - "lifecycle"
  - "stubs"
  - "promotion"
  - "git-pr"
  - "hitl"
---

# ナレッジ・ライフサイクル ＆ 二段階昇格仕様 (v7.0)

原本バイナリの肥大化を防ぎ、未完成な AI 下書き（スタブ）による本番 Vault の汚染を隔離し、人間と AI の自律協調を安全に回すための拡張ライフサイクルモデル。

## ライフサイクル遷移

```text
[ 投入: _raw/ ] ──(Doclingパース)──> [ 検証: staging/ ]
                                            │
                                  (status: reviewed 変更)
                                            ▼
[ 退避: raw_sources/ ] <──(原本退避)── [ 本番: wiki/ ]
                                            │
                             (未解決赤リンク検知)
                                            ▼
                               [ 隔離: wiki/stubs/ ] (status: draft)
                                            │
                      (バックリンク蓄積による自動逆合成 or 人間査読)
                                            ▼
                             [ 昇格: wiki/concepts/ ] (status: stable)
```

## 各フェーズの役割

1. **投入フェーズ (`_raw/`)**: 原本バイナリ（PDF/DOCX/PPTX/XLSX等）を投入。
2. **検証フェーズ (`staging/`)**: 未審査ノート (`status: draft` / `unreviewed`) と画像アセットが配置され、レビューを待機。
3. **隔離スタブフェーズ (`wiki/stubs/`)**: リンク切れの赤リンクを検知した際、本番を汚さず隔離起票される下書き（`status: draft`）。
4. **本番昇格フェーズ (`wiki/concepts/`, `wiki/papers/` 等)**:
   - 逆合成完了または人間による査読承認（`wikid-steward review`）により、`status: stable` へ自動昇格移動。
5. **退避フェーズ (`raw_sources/`)**: 昇格と同時に原本バイナリが Git 管理外のアーカイブフォルダへ物理移動。

## Git ブランチ ＆ PR 協調モデル

- AI の自動バックグラウンドコンパイル処理は `main` ブランチに直接プッシュせず、**`steward/auto-compiler`** ブランチにコミット・プッシュして Pull Request を自動作成。
- コミットメッセージに `[skip ci]` を付与し、CI 無限ループを防止。
- 人間のローカル編集との衝突（デッドロック）を完全に排除。

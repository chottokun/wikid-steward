# 実装計画: LLM推論堅牢化・タイムアウト回復・処理性能最適化

## 1. 概要 (Overview)
`DocumentToOKFCompiler` および `GlossaryExtractor` における LLM/VLM 連携処理の安定性・高速性・耐障害性を高めるための改善計画。

---

## 2. 課題と背景 (Issues & Background)
1. **極小・空テキストの無駄な推論レイテンシ**:
   - 0バイトや極小テキスト（10文字未満など）に対して LLM API を呼び出すと、不要なネットワーク/推論待ち時間が発生する（※ `GlossaryExtractor` 側で10文字未満スキップガードを先行適用済み）。
2. **LLM タイムアウトとハングアップのリスク**:
   - ローカル Ollama やリモート LLM が高負荷時に応答不能となった場合、クライアントが長時間ブロックされバッチコンパイル全体が停止する恐れがある。
3. **タイムアウト時のリカバリー（フォールバック）戦略**:
   - タイムアウト発生時に例外でプロセスを落とすのではなく、どのように安全にフォールバックして処理を継続するかの標準仕様が必要。

---

## 3. 実装候補・仕様 (Proposed Implementations)

### ① LLM クライアントの明示的タイムアウト設定
* **対象**: `src/wikid_steward/core/llm_client.py`, `config.yaml`
* **仕様**:
  * `config.yaml` の `llm:` セクションに `timeout: 30.0` (秒) を追加。
  * `OpenAI(base_url=..., api_key=..., timeout=cfg.llm.timeout)` を設定し、指定秒数以上応答がない場合は即座に `APITimeoutError` を送出する。

### ② タイムアウト・API障害時のフォールバック & リカバリー戦略
* **対象**: `src/wikid_steward/core/glossary.py`, `src/wikid_steward/core/document_compiler.py`
* **リカバリー手順**:
  1. **リトライ**: 指数バックオフ（1秒、2秒）で最大2回まで再試行。
  2. **ヒューリスティック・フォールバック (Graceful Degradation)**:
     - リトライ後もタイムアウトした場合は、例外で落とさずに警告ログ（`logger.warning`）を出力。
     - **ルールベース抽出への切り替え**: 見出し（`#`, `##`）や太字（`**...**`）、大文字英字略語（`LoRA`, `RAG` 等）を正規表現で簡易抽出し、用語ノートのスタブを作成。
     - 生成ノートのフロントマター `provenance` に `inferred_by: "heuristic_fallback (llm_timeout)"` を記録。
  3. **コンパイル全体の完遂**:
     - メインノート（`wiki/{slug}.md`）および生Markdown（`_raw/{slug}.md`）の生成・保存は 100% 成功させる。

### ③ 最小テキスト長判定のコンフィグ化
* **対象**: `config.yaml`, `src/wikid_steward/core/config.py`
* **仕様**:
  * `relinker.min_extract_chars: 15` などを設定可能にし、短すぎるテキストは用語抽出を自動バイパス。

---

## 4. 検証計画 (Verification Plan)
- [ ] タイムアウト（`timeout=0.001` 等）をモックしたフォールバック単体テストの追加
- [ ] タイムアウト発生時でもメインノートが正常生成される E2E 検証
- [ ] `provenance` にフォールバック情報が正確に記録されることの検証

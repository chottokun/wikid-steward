---
type: "Architecture Decision"
title: "FastMCP サーバー統合 ＆ LLM クライアント連携仕様"
sources:
  - resource: "/src/wikid_steward/mcp/server.py"
  - resource: "/src/wikid_steward/cli.py"
status: "stable"
generated:
  by: "agent/antigravity"
  at: "2026-08-19T21:40:00Z"
description: "FastMCP を用いた MCP サーバー機能、公開ツール・リソース仕様、Claude Desktop 等の外部クライアント設定および呼び出し手順"
tags:
  - "mcp"
  - "fastmcp"
  - "llm-integration"
  - "claude-desktop"
---

# FastMCP サーバー統合 ＆ LLM クライアント連携仕様

`wikid-steward` は **FastMCP** を採用し、Claude Desktop や Cursor、Antigravity などの LLM クライアントからナレッジベースへ直接アクセスできる Model Context Protocol (MCP) サーバーを提供しています。

---

## 1. FastMCP サーバーのアーキテクチャ

`wikid-steward` の MCP サーバー（`src/wikid_steward/mcp/server.py`）は、ナレッジの読み取り専用リソースと、保守・検索・コンパイル用の各種ツールを LLM に公開します。

```
[Claude Desktop / LLM Client]
          │
          │ (stdio / sse)
          ▼
   [FastMCP Server] (wikid-steward mcp)
    ├── Resources: wiki://{path} (ノート・生Markdown参照)
    └── Tools:
         ├── search: 1-Hop ナレッジグラフ検索 ＆ 統合要約
         ├── compile_stub: バックリンク蓄積スタブの自動逆合成
         ├── lint: リンク切れ監査 ＆ スタブ自動起票
         ├── moc: 目次インデックス (index.md) 自動再編成
         └── compile_document: ドキュメントの OKF Markdown 分解
```

---

## 2. 公開リソース (Resources)

### `wiki://{path}`
Wiki 内の任意の Markdown ノートやアセットの内容を直接読み出します。

* **URI 形式**: `wiki://concepts/pid-control.md`, `wiki://raw_markdown/paper_summary.md` 等
* **セキュリティガード**: `wiki/` ディレクトリ外へのパストラバーサル（`../`）アクセスは自動的に拒否（`ValueError`）されます。
* **戻り値**: 指定された Markdown ファイルのプレーンテキスト。

---

## 3. 公開ツール (Tools)

| ツール名 | 説明 | 主要引数 | 戻り値例 |
| :--- | :--- | :--- | :--- |
| **`search`** | 1-Hop グラフ巡回と PageRank ブースト付きナレッジ検索 | `query` (str)<br>`top_k` (int, default: 3)<br>`backend` (str, "auto"\|"qdrant"\|"lightweight")<br>`doc_types` (list[str], 任意) | `main_hits`, `traversed_glossary_terms`, `integrated_answer` |
| **`compile_stub`** | 蓄積バックリンクから未定義用語スタブを自動逆合成 | `term` (str)<br>`force` (bool, default: False) | `success`, `promoted_path` |
| **`lint`** | Wiki ナレッジベースの健全性監査と未定義リンクのスタブ起票 | `dry_run` (bool, default: False) | `total_files`, `is_healthy`, `stubs_created`, `issues` |
| **`moc`** | 全カテゴリの目次インデックス (`index.md`) を自動再構成 | (なし) | `generated_mocs` |
| **`compile_document`** | ドキュメント（PDF等）を OKF v0.2 Markdown 群に分解コンパイル | `file_path` (str)<br>`status` (str, default: "draft") | `success`, `raw_markdown_path`, `main_note_path`, `concept_count` |

---

## 4. 利用手順 ＆ クライアント設定

### 4.1 CLI からの起動
```bash
# 標準入出力 (stdio) モードで起動（Claude Desktop 等の標準）
uv run wikid-steward mcp --transport stdio

# SSE (Server-Sent Events) モードで起動（Web/リモート連携用）
uv run wikid-steward mcp --transport sse
```

### 4.2 Claude Desktop への登録設定
Claude Desktop の設定ファイル（`claude_desktop_config.json`）に以下のように追記します。

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Linux**: `~/.config/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "wikid-steward": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/wikid-steward",
        "run",
        "wikid-steward",
        "mcp",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

> [!TIP]
> `--directory` に `wikid-steward` のプロジェクトルート絶対パスを指定することで、どのディレクトリから Claude を起動しても自身の Vault を正しく認識します。

### 4.3 Python スクリプトからの直接呼び出し例
FastMCP Client を利用してプログラムからサーバー機能を呼び出す例です：

```python
import asyncio
from pathlib import Path
from fastmcp import Client
from wikid_steward.mcp.server import mcp

async def main():
    async with Client(mcp) as client:
        # 1. リソースの読み込み
        content = await client.read_resource("wiki://concepts/sample.md")
        print("=== Note Content ===")
        print(content)

        # 2. 検索ツールの呼び出し (Concept ノートのみにスコープ絞り込み)
        result = await client.call_tool("search", {
            "query": "PID制御のチューニング方法",
            "top_k": 3,
            "doc_types": ["Concept"]
        })
        print("=== Search Result ===")
        print(result.content)

        # 3. Linter 監査の実行
        lint_result = await client.call_tool("lint", {"dry_run": True})
        print("=== Lint Report ===")
        print(lint_result.content)

if __name__ == "__main__":
    asyncio.run(main())
```

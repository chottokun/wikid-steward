from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from wikid_steward.core.config import get_config
from wikid_steward.core.document_compiler import DocumentToOKFCompiler
from wikid_steward.core.linter import KnowledgeLinter
from wikid_steward.core.moc_generator import generate_all_mocs
from wikid_steward.core.retro_compiler import RetroCompiler
from wikid_steward.vector.searcher import create_search_engine

mcp = FastMCP("wikid-steward")


@mcp.resource("wiki://{path}")
def get_wiki_resource(path: str) -> str:
    """Wiki ノートまたはアセットの内容を取得する"""
    cfg = get_config()
    wiki_dir = (Path.cwd() / cfg.paths.wiki_dir).resolve()
    target_path = (wiki_dir / path).resolve()

    if not target_path.is_relative_to(wiki_dir):
        raise ValueError(f"Access denied: path '{path}' is outside wiki directory")

    if not target_path.exists() or not target_path.is_file():
        raise FileNotFoundError(f"Resource not found: {path}")

    return target_path.read_text(encoding="utf-8")


@mcp.tool()
def search(
    query: str,
    top_k: int = 3,
    backend: str = "auto",
    doc_types: list[str] | None = None,
) -> dict[str, Any]:
    """wikid-steward のナレッジベースを 1-Hop グラフ巡回で検索し統合回答を生成する (doc_types で絞り込み可能)"""
    cfg = get_config()
    wiki_dir = Path.cwd() / cfg.paths.wiki_dir
    engine = create_search_engine(backend=backend)
    res = engine.search(query=query, wiki_dir=wiki_dir, top_k=top_k, doc_types=doc_types)

    return {
        "query": res.query,
        "main_hits": res.main_hits,
        "traversed_glossary_terms": res.traversed_glossary_terms,
        "integrated_answer": res.integrated_answer,
    }


@mcp.tool()
def compile_stub(term: str, force: bool = False) -> dict[str, Any]:
    """累積されたバックリンク文脈から未定義用語スタブを自動逆合成し本番へ昇格させる"""
    cfg = get_config()
    wiki_dir = Path.cwd() / cfg.paths.wiki_dir
    compiler = RetroCompiler(
        wiki_dir=wiki_dir,
        min_backlinks=cfg.retro_compilation.min_backlinks,
        target_language=cfg.llm.target_language,
    )
    promoted = compiler.compile_stub(term=term, force=force)
    if promoted:
        return {"success": True, "promoted_path": str(promoted.relative_to(Path.cwd()))}
    return {
        "success": False,
        "message": f"Stub for [[{term}]] could not be compiled. Use force=True to force compile.",
    }


@mcp.tool()
def lint(dry_run: bool = False) -> dict[str, Any]:
    """Wiki ナレッジベースの健全性監査と未定義リンクの自動スタブ起票を実行する"""
    cfg = get_config()
    wiki_dir = Path.cwd() / cfg.paths.wiki_dir
    linter = KnowledgeLinter(wiki_dir)
    report = linter.run_lint(auto_create_stubs=not dry_run)

    return {
        "total_files": report.total_files,
        "is_healthy": report.is_healthy,
        "stubs_created": report.stubs_created,
        "issues": [
            {"file": i.file_path, "type": i.issue_type, "message": i.message} for i in report.issues
        ],
    }


@mcp.tool()
def moc() -> dict[str, Any]:
    """Wiki カテゴリ別の目次インデックス (index.md) を自動再構成する"""
    cfg = get_config()
    wiki_dir = Path.cwd() / cfg.paths.wiki_dir
    mocs = generate_all_mocs(wiki_dir)
    return {
        "generated_mocs": [str(m.relative_to(Path.cwd())) for m in mocs],
    }


@mcp.tool()
def compile_document(file_path: str, status: str = "draft") -> dict[str, Any]:
    """ドキュメント (PDF, Markdown等) を OKF v0.2 Markdown 群にコンパイルする"""
    compiler = DocumentToOKFCompiler(base_dir=Path.cwd())
    doc_path = Path(file_path).resolve()

    if not doc_path.exists():
        return {"success": False, "message": f"File not found: {file_path}"}

    res = compiler.compile_file(file_path=doc_path, status=status)
    return {
        "success": True,
        "raw_markdown_path": str(res.raw_markdown_path.relative_to(Path.cwd())),
        "main_note_path": str(res.main_note_path.relative_to(Path.cwd())),
        "concept_count": len(res.concept_note_paths),
    }


def run_mcp_server(transport: str = "stdio") -> None:
    """FastMCP サーバーの起動エントリポイント"""
    mcp.run(transport=transport)


if __name__ == "__main__":
    run_mcp_server()

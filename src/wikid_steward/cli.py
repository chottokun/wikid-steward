import logging
from pathlib import Path
import click

from wikid_steward.watcher.daemon import start_daemon

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@click.group()
def main():
    """wikid-steward: LLM Wiki Simple Reboot Knowledge Manager CLI"""
    pass


@main.command()
@click.option(
    "--dir",
    "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path.cwd(),
    help="Target base directory",
)
def run(dir: Path):
    """Run real-time watching daemon for _raw/ and staging/"""
    click.echo(f"Starting wikid-steward daemon in {dir}...")
    start_daemon(dir)


@main.command()
@click.argument("query", type=str)
@click.option(
    "--dir",
    "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path.cwd(),
    help="Target base directory",
)
@click.option(
    "--top-k",
    "-k",
    type=int,
    default=3,
    help="Top K search hits",
)
def search(query: str, dir: Path, top_k: int):
    """Run LLM-Wiki Graph-Augmented Search over wiki/ directory"""
    click.echo(f"🔍 Running Wiki-Graph Search for query: '{query}'...")

    wiki_dir = dir / "wiki"
    if not wiki_dir.exists():
        click.echo(f"Warning: wiki directory not found at {wiki_dir}")

    from wikid_steward.vector.indexer import QdrantKnowledgeIndexer
    from wikid_steward.vector.searcher import WikiGraphSearchEngine

    indexer = QdrantKnowledgeIndexer(location=":memory:")
    indexed_count = indexer.index_wiki_directory(wiki_dir)
    click.echo(f"  -> Indexed {indexed_count} knowledge chunks from {wiki_dir}")

    search_engine = WikiGraphSearchEngine(indexer=indexer)
    result = search_engine.search(query=query, wiki_dir=wiki_dir, top_k=top_k)

    click.echo("\n" + "=" * 60)
    click.echo(" 📌 【メイン該当ノート (Qdrant Hits)】")
    for i, hit in enumerate(result.main_hits, 1):
        click.echo(f" [{i}] {hit.get('title')} ({hit.get('file_path')})")

    if result.traversed_glossary_terms:
        click.echo("\n 🔗 【巡回抽出された WikiLink 用語 (1-Hop Traversal)】")
        for g in result.traversed_glossary_terms:
            click.echo(f" ・[[{g['term']}]] ({g['file']})")

    click.echo("\n 💡 【LLM 統合要約回答】")
    click.echo(result.integrated_answer)
    click.echo("=" * 60 + "\n")


if __name__ == "__main__":
    main()

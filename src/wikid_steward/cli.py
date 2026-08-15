import logging
from pathlib import Path
import click

from wikid_steward.core.config import get_config
from wikid_steward.core.graph_searcher import LightweightGraphSearchEngine
from wikid_steward.core.linter import KnowledgeLinter
from wikid_steward.core.moc_generator import generate_all_mocs
from wikid_steward.core.resolver import resolve_git_conflict
from wikid_steward.core.retro_compiler import RetroCompiler
from wikid_steward.core.reviewer import review_file
from wikid_steward.watcher.daemon import start_daemon

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@click.group()
def main():
    """wikid-steward: LLM Wiki Simple Reboot Knowledge Manager CLI (v7.0)"""
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
@click.argument(
    "file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--dir",
    "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path.cwd(),
    help="Target base directory",
)
def compile(file: Path, dir: Path):
    """Compile a raw source or staging file into structured OKF notes"""
    click.echo(f"⚙️ Compiling {file} into knowledge notes...")
    from wikid_steward.watcher.handlers import StagingFileHandler
    handler = StagingFileHandler(dir)
    handler.process_staging_file(file)
    click.echo(f"✅ Compilation finished for {file.name}")


@main.command("compile-stub")
@click.argument("term", type=str)
@click.option(
    "--dir",
    "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path.cwd(),
    help="Target base directory",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force compilation even if backlinks count is below threshold",
)
def compile_stub_cmd(term: str, dir: Path, force: bool):
    """Retro-compile a stub note from accumulated backlink contexts"""
    cfg = get_config()
    wiki_dir = dir / cfg.paths.wiki_dir
    click.echo(f"🧠 Retro-compiling stub for term: [[{term}]]...")

    compiler = RetroCompiler(
        wiki_dir=wiki_dir,
        min_backlinks=cfg.retro_compilation.min_backlinks,
        target_language=cfg.llm.target_language,
    )
    promoted = compiler.compile_stub(term=term, force=force)
    if promoted:
        click.echo(f"🎉 Successfully synthesized and promoted to {promoted.relative_to(dir)}")
    else:
        click.echo(f"⚠️ Stub for [[{term}]] could not be compiled (insufficient backlinks or stub not found). Use --force to override.")


@main.command()
@click.argument(
    "file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--reviewer",
    "-r",
    type=str,
    default="human:reviewer",
    help="Reviewer identifier (e.g. human:username)",
)
@click.option(
    "--dir",
    "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path.cwd(),
    help="Target base directory",
)
def review(file: Path, reviewer: str, dir: Path):
    """Review a note, record verification log, and promote to stable"""
    cfg = get_config()
    wiki_dir = dir / cfg.paths.wiki_dir
    promoted_file = review_file(file_path=file, reviewer=reviewer, wiki_dir=wiki_dir)
    click.echo(f"✅ Verified by '{reviewer}'. Promoted/updated at {promoted_file.relative_to(dir)}")


@main.command()
@click.argument(
    "file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def resolve(file: Path):
    """Automatically resolve Git conflict markers in a markdown note"""
    click.echo(f"🔧 Resolving Git conflict markers in {file.name}...")
    success = resolve_git_conflict(file)
    if success:
        click.echo(f"✅ Successfully resolved conflicts in {file.name}")
    else:
        click.echo(f"❌ Failed to resolve conflicts in {file.name}")


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
    """Run lightweight Graph-Augmented Search over wiki/ directory"""
    click.echo(f"🔍 Running Lightweight Wiki-Graph Search for query: '{query}'...")
    cfg = get_config()
    wiki_dir = dir / cfg.paths.wiki_dir

    engine = LightweightGraphSearchEngine()
    result = engine.search(query=query, wiki_dir=wiki_dir, top_k=top_k)

    click.echo("\n" + "=" * 60)
    click.echo(" 📌 【メイン該当ノート (Direct Hits)】")
    for i, hit in enumerate(result.main_hits, 1):
        click.echo(f" [{i}] {hit.get('title')} ({hit.get('file_path')}) - Score: {hit.get('score'):.1f}")

    if result.traversed_glossary_terms:
        click.echo("\n 🔗 【巡回抽出された WikiLink 用語 (1-Hop Traversal)】")
        for g in result.traversed_glossary_terms:
            click.echo(f" ・[[{g['term']}]] ({g['file']})")

    click.echo("\n 💡 【LLM 統合要約回答】")
    click.echo(result.integrated_answer)
    click.echo("=" * 60 + "\n")


@main.command()
@click.option(
    "--dir",
    "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path.cwd(),
    help="Target base directory",
)
def moc(dir: Path):
    """Generate dynamic Map of Content (index.md) for all categories in wiki/"""
    cfg = get_config()
    wiki_dir = dir / cfg.paths.wiki_dir
    click.echo(f"🗺️ Generating dynamic MOCs for {wiki_dir}...")
    mocs = generate_all_mocs(wiki_dir)
    click.echo(f"✅ Generated {len(mocs)} MOC files:")
    for m in mocs:
        click.echo(f"  - {m.relative_to(dir)}")


@main.command()
@click.option(
    "--dir",
    "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path.cwd(),
    help="Target base directory",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Do not create stub notes; only audit issues and suggest typos",
)
def lint(dir: Path, dry_run: bool):
    """Lint and verify integrity of wiki/ knowledge base"""
    cfg = get_config()
    wiki_dir = dir / cfg.paths.wiki_dir
    click.echo(f"🛡️ Running Knowledge Lint & Self-Healing audit for {wiki_dir}...")

    linter = KnowledgeLinter(wiki_dir)
    report = linter.run_lint(auto_create_stubs=not dry_run)

    click.echo(f"Scanned {report.total_files} files.")
    if report.stubs_created:
        click.echo(f"🌱 Created {len(report.stubs_created)} stub notes in wiki/stubs/:")
        for s in report.stubs_created:
            click.echo(f"  - wiki/stubs/{s}.md")

    if report.is_healthy:
        click.echo("🎉 HEALTHY! 0 fatal issues found in knowledge base.")
    else:
        click.echo(f"⚠️ Found {len(report.issues)} issue(s):")
        for issue in report.issues:
            click.echo(f"  - [{issue.issue_type}] {issue.file_path}: {issue.message}")


if __name__ == "__main__":
    main()

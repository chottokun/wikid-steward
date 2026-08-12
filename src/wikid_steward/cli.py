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


if __name__ == "__main__":
    main()

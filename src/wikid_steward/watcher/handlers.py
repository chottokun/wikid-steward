import logging
from pathlib import Path
from watchdog.events import FileSystemEvent, FileSystemEventHandler

from wikid_steward.core.config import get_config
from wikid_steward.core.document_compiler import DocumentToOKFCompiler
from wikid_steward.core.promoter import check_reviewed_status, promote_document

logger = logging.getLogger(__name__)


class StagingFileHandler:
    """staging/ または _raw/ からの手動/自動コンパイルをハンドリングするクラス"""

    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.compiler = DocumentToOKFCompiler(base_dir=self.base_dir)

    def process_staging_file(
        self,
        file_path: Path,
        status: str = "draft",
        reviewer: str | None = None,
        save_source: bool = True,
        hide_source_links: bool = False,
        extract_terms: bool = True,
    ) -> None:
        """単一ファイルをコンパイルして OKF Markdown 群を生成する"""
        logger.info(f"Processing compilation for {file_path}")
        self.compiler.compile_file(
            file_path=file_path,
            status=status,
            reviewer=reviewer,
            save_source=save_source,
            hide_source_links=hide_source_links,
            extract_terms=extract_terms,
        )

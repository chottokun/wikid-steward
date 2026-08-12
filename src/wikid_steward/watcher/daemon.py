import logging
from pathlib import Path
import time
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from wikid_steward.core.metadata_embedder import (
    embed_png_metadata,
    prepare_clean_assets_dir,
)
from wikid_steward.core.okf_converter import (
    generate_okf_frontmatter,
    replace_image_links,
)
from wikid_steward.core.parser import KnowledgeParser
from wikid_steward.core.profiles import resolve_profile
from wikid_steward.core.promoter import check_reviewed_status, promote_document
from wikid_steward.core.slug import generate_slug

logger = logging.getLogger(__name__)


class RawFolderHandler(FileSystemEventHandler):
    """_raw/ ディレクトリへの原本バイナリ投入を監視し、staging/ へのパース配置を行うハンドラー"""

    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self.raw_dir = base_dir / "_raw"
        self.staging_dir = base_dir / "staging"
        self.wiki_dir = base_dir / "wiki"
        self.parser = KnowledgeParser()

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._process_raw_file(Path(event.src_path))

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._process_raw_file(Path(event.src_path))

    def _process_raw_file(self, file_path: Path) -> None:
        # パス相対関係
        try:
            rel_path = file_path.relative_to(self.raw_dir)
        except ValueError:
            return

        # 対応拡張子チェック
        if file_path.suffix.lower() not in [
            ".pdf",
            ".docx",
            ".pptx",
            ".xlsx",
        ]:
            return

        # スラッグ生成 ＆ プロファイル解決
        rel_no_ext = str(rel_path.with_suffix(""))
        slug = generate_slug(rel_no_ext)
        profile, prof_source, custom_meta = resolve_profile(
            file_path, self.raw_dir
        )

        # 冪等性チェック: wiki/ に既に reviewed ノートが存在する場合は上書き防止のため処理スキップ
        wiki_note = self.wiki_dir / rel_path.parent / f"{slug}.md"
        if wiki_note.exists() and check_reviewed_status(wiki_note):
            logger.info(
                f"[SKIP] {slug} already exists in wiki/ (status: reviewed). Bypassing ingest."
            )
            return

        logger.info(
            f"[INGEST] Processing raw file: {rel_path} -> slug: {slug} (profile: {profile.name}, source: {prof_source})"
        )

        try:
            # 1. Docling パースの実行 (プロファイル設定を反映)
            conv_result = self.parser.parse(file_path, profile=profile)
            doc_md = conv_result.document.export_to_markdown()

            # 2. アセットクリーンアップと画像埋め込み
            staging_note_dir = self.staging_dir / rel_path.parent
            staging_assets_dir = prepare_clean_assets_dir(
                staging_note_dir / "assets" / slug
            )

            # 画像出力・【層B】メタデータ埋め込み
            if hasattr(conv_result.document, "pictures"):
                for i, pic in enumerate(conv_result.document.pictures):
                    img_name = f"fig{i + 1}.png"
                    img_path = staging_assets_dir / img_name
                    if hasattr(pic, "image") and pic.image:
                        pic.image.pil_image.save(img_path)
                        meta_payload = {
                            "uuid": f"img_{slug}_crop{i + 1:02d}",
                            "parent_doc_id": slug,
                            "original_source": str(
                                Path("raw_sources") / rel_path
                            ),
                            "page_number": getattr(pic, "page_no", 1),
                        }
                        embed_png_metadata(img_path, meta_payload)

            # 3. OKF 【層A】 Frontmatter 付与 (トレーサビリティプロパティ追加) & Markdown 置換
            frontmatter = generate_okf_frontmatter(
                doc_id=slug,
                title=file_path.stem,
                doc_type=profile.doc_type,
                source_path=str(Path("raw_sources") / rel_path),
                profile_used=profile.name,
                profile_source=prof_source,
                custom_metadata=custom_meta,
            )
            body = replace_image_links(doc_md, slug)
            final_content = f"{frontmatter}\n{body}"

            # 4. staging/ への配置
            staging_note = staging_note_dir / f"{slug}.md"
            staging_note_dir.mkdir(parents=True, exist_ok=True)
            staging_note.write_text(final_content, encoding="utf-8")

            logger.info(f"[SUCCESS] Staged notebook: {staging_note}")

        except Exception as e:
            logger.error(f"[ERROR] Failed to ingest {rel_path}: {e}")


class StagingFolderHandler(FileSystemEventHandler):
    """staging/ 内のステータス更新 (status: reviewed) を 1s デバウンスで監視し昇格を行うハンドラー"""

    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self.staging_dir = base_dir / "staging"
        self._last_modified: dict[str, float] = {}

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and event.src_path.endswith(".md"):
            self._check_and_promote(Path(event.src_path))

    def _check_and_promote(self, note_path: Path) -> None:
        if not note_path.exists():
            return

        # 1秒のデバウンス制御
        now = time.time()
        mtime = note_path.stat().st_mtime
        if now - mtime < 1.0:
            return

        if check_reviewed_status(note_path):
            logger.info(
                f"[PROMOTE] Promoted status detected for {note_path.name}"
            )
            # 原本相対パスの推測
            try:
                rel_path = note_path.relative_to(self.staging_dir)
                raw_rel_pdf = rel_path.parent / f"{note_path.stem}.pdf"
            except ValueError:
                raw_rel_pdf = None

            promote_document(
                staging_note=note_path,
                base_dir=self.base_dir,
                raw_relative_path=raw_rel_pdf,
                commit_git=True,
            )
            logger.info(f"[SUCCESS] Promoted {note_path.name} to wiki/")


def start_daemon(base_dir: Path | str) -> None:
    """_raw ディレクトリおよび staging ディレクトリのリアルタイム監視デーモンを開始する"""
    base = Path(base_dir)
    observer = Observer()

    raw_handler = RawFolderHandler(base)
    staging_handler = StagingFolderHandler(base)

    (base / "_raw").mkdir(parents=True, exist_ok=True)
    (base / "staging").mkdir(parents=True, exist_ok=True)

    observer.schedule(raw_handler, str(base / "_raw"), recursive=True)
    observer.schedule(staging_handler, str(base / "staging"), recursive=True)

    observer.start()
    logger.info(f"[DAEMON] Started wikid-steward daemon watching {base}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

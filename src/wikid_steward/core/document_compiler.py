from dataclasses import dataclass, field
import logging
from pathlib import Path
import shutil
from typing import Any

from wikid_steward.core.config import AppConfig, get_config
from wikid_steward.core.glossary import GlossaryExtractor, GlossaryTerm
from wikid_steward.core.handlers import get_profile_handler
from wikid_steward.core.human_memo import HUMAN_MEMO_TEMPLATE, merge_human_memo
from wikid_steward.core.llm_client import OpenAICompatibleLLMClient
from wikid_steward.core.metadata_embedder import (
    embed_png_metadata,
    prepare_clean_assets_dir,
)
from wikid_steward.core.okf_converter import (
    ActorInfo,
    OKFDocumentData,
    SourceEntry,
    VerifiedEntry,
    generate_okf_v7_frontmatter,
    parse_okf_frontmatter,
    replace_image_links,
)
from wikid_steward.core.parser import KnowledgeParser
from wikid_steward.core.profiles import resolve_profile
from wikid_steward.core.relinker import WikiRelinker
from wikid_steward.core.slug import generate_slug

logger = logging.getLogger(__name__)


@dataclass
class CompilationResult:
    """ドキュメントコンパイル結果"""

    raw_markdown_path: Path
    main_note_path: Path
    concept_note_paths: list[Path] = field(default_factory=list)
    extracted_images: list[Path] = field(default_factory=list)
    saved_source_path: Path | None = None


class DocumentToOKFCompiler:
    """様々な原本ドキュメント（PDF, DOCX, PPTX, XLSX, Markdown, テキスト等）を

    OKF v0.2 思想に準拠した Markdown 群（生Markdown、メインノート、概念・用語ノート群）に
    変換・コンパイルするオーケストレーター。
    """

    def __init__(
        self,
        base_dir: Path | str | None = None,
        config: AppConfig | None = None,
        parser: KnowledgeParser | None = None,
        llm_client: OpenAICompatibleLLMClient | None = None,
    ):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.config = config or get_config()
        self.parser = parser
        self.llm_client = llm_client

    def compile_file(
        self,
        file_path: Path | str,
        output_dir: Path | None = None,
        status: str = "draft",
        reviewer: str | None = None,
        save_source: bool = True,
        hide_source_links: bool = False,
        extract_terms: bool = True,
        profile_name: str | None = None,
    ) -> CompilationResult:
        """単一ドキュメントファイルを OKF v0.2 準拠の Markdown 群にコンパイルする。

        Args:
            file_path: 変換対象ファイルパス
            output_dir: 出力先メインディレクトリ（デフォルトは wiki/）
            status: 文書ステータス ("draft" | "stable" | "deprecated")
            reviewer: 査読者識別子（指定された場合 verified に記録）
            save_source: 原本バイナリを sources/ にコピー保存するかどうか
            hide_source_links: 原本への実パス・リンクを非表示・マスクするかどうか
            extract_terms: 用語・概念ノートを分解抽出するかどうか
            profile_name: 明示的なプロファイル名指定

        Returns:
            CompilationResult: 生成されたファイル群のパス情報
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = self.base_dir / path

        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Source file not found: {path}")

        slug = generate_slug(path.stem)
        title = path.stem

        # 出力先ディレクトリの決定
        raw_dir = self.base_dir / self.config.paths.raw_dir
        raw_sources_dir = self.base_dir / self.config.paths.raw_sources_dir
        wiki_dir = output_dir or (self.base_dir / self.config.paths.wiki_dir)
        concepts_dir = wiki_dir / "concepts"
        assets_base_dir = wiki_dir / "assets"

        raw_dir.mkdir(parents=True, exist_ok=True)
        wiki_dir.mkdir(parents=True, exist_ok=True)
        concepts_dir.mkdir(parents=True, exist_ok=True)

        # 1. プロファイルの解決
        profile, prof_source, custom_meta = resolve_profile(path, self.base_dir)
        if profile_name:
            from wikid_steward.core.profiles import get_profile_by_name

            p = get_profile_by_name(profile_name)
            if p:
                profile = p

        # 2. 原本バイナリの保存 (save_source=True の場合)
        saved_source_path: Path | None = None
        source_rel_path = f"raw_sources/{path.name}"
        if save_source:
            raw_sources_dir.mkdir(parents=True, exist_ok=True)
            saved_source_path = raw_sources_dir / path.name
            if path != saved_source_path:
                shutil.copy2(path, saved_source_path)
            source_rel_path = str(saved_source_path.relative_to(self.base_dir))

        # ソース参照パスの調整（hide_source_links対応）
        source_resource_path = "" if hide_source_links else source_rel_path

        # 3. ドキュメントのパースとテキスト・画像アセット抽出
        raw_extracted_text = ""
        extracted_image_names: list[str] = []
        extracted_image_paths: list[Path] = []
        staging_assets_dir = prepare_clean_assets_dir(assets_base_dir / slug)

        suffix = path.suffix.lower()
        if suffix in [".pdf", ".docx", ".pptx", ".xlsx"]:
            if self.parser is None:
                self.parser = KnowledgeParser()

            conv_result = self.parser.parse(path, profile=profile)
            raw_extracted_text = conv_result.document.export_to_markdown()

            if hasattr(conv_result.document, "pictures"):
                for i, pic in enumerate(conv_result.document.pictures):
                    img_name = f"fig{i + 1}.png"
                    img_path = staging_assets_dir / img_name
                    if hasattr(pic, "image") and pic.image:
                        pic.image.pil_image.save(img_path)
                        meta_payload = {
                            "uuid": f"img_{slug}_crop{i + 1:02d}",
                            "parent_doc_id": slug,
                            "original_source": "" if hide_source_links else source_rel_path,
                            "page_number": getattr(pic, "page_no", 1),
                        }
                        embed_png_metadata(img_path, meta_payload)
                        extracted_image_names.append(img_name)
                        extracted_image_paths.append(img_path)
        else:
            # Markdown, テキスト, HTMLなどのプレーンテキスト
            raw_extracted_text = path.read_text(encoding="utf-8")
            # 既にフロントマターがある場合は分離
            _, body_content = parse_okf_frontmatter(raw_extracted_text)
            raw_extracted_text = body_content

        # プロファイルハンドラーによる後処理（SBOM表やフォーマット調整）
        handler = get_profile_handler(profile.name)
        raw_processed_md = handler.post_process_markdown(raw_extracted_text, profile.name)

        # 抽出画像アセットの Markdown リンク置換および埋め込み
        raw_processed_md = replace_image_links(
            raw_processed_md, slug, extracted_image_names=extracted_image_names
        )

        # 4. _raw/{slug}.md への生Markdown（OKF YAML付き・画像埋め込み・手書きメモ完備）保存
        raw_sources_list = []
        if source_resource_path or not hide_source_links:
            raw_sources_list.append(
                SourceEntry(
                    id="source",
                    resource=source_resource_path,
                    title=title,
                )
            )

        raw_okf_doc = OKFDocumentData(
            doc_type="Source",
            title=title,
            description=f"Raw ingested markdown source from {path.name}",
            status=status,
            generated=ActorInfo(by="wikid-steward/compiler"),
            sources=raw_sources_list,
            tags=["raw_source", profile.name],
            custom_metadata=custom_meta,
        )
        if reviewer:
            raw_okf_doc.verified = [VerifiedEntry(by=reviewer)]

        raw_fm_str = generate_okf_v7_frontmatter(raw_okf_doc)
        raw_markdown_path = raw_dir / f"{slug}.md"
        existing_raw_content = (
            raw_markdown_path.read_text(encoding="utf-8")
            if raw_markdown_path.exists()
            else None
        )

        raw_body_with_memo = (
            f"{raw_processed_md}\n\n{HUMAN_MEMO_TEMPLATE}"
            if "## 📝 手書きメモ" not in raw_processed_md
            else raw_processed_md
        )
        final_raw_content = merge_human_memo(
            f"{raw_fm_str}\n{raw_body_with_memo}", existing_raw_content
        )
        raw_markdown_path.write_text(final_raw_content, encoding="utf-8")

        # 5. 用語・概念の分解・抽出 (extract_terms=True の場合)
        concept_paths: list[Path] = []
        extracted_terms: list[GlossaryTerm] = []

        if extract_terms:
            extractor = GlossaryExtractor(llm_client=self.llm_client)
            # ルールベース/LLM抽出
            extracted_terms = extractor.extract_terms(raw_extracted_text)

            # 各概念について 1トピック=1ファイル の OKF ノートを生成
            for term in extracted_terms:
                concept_slug = term.slug or generate_slug(term.canonical_title)
                concept_note_path = concepts_dir / f"{concept_slug}.md"

                # 既存ノートが存在する場合は手書きメモを保護
                existing_content = (
                    concept_note_path.read_text(encoding="utf-8")
                    if concept_note_path.exists()
                    else None
                )

                concept_sources = []
                if source_resource_path or not hide_source_links:
                    concept_sources.append(
                        SourceEntry(
                            id=slug,
                            resource=source_resource_path,
                            title=title,
                        )
                    )

                concept_doc = OKFDocumentData(
                    doc_type="Concept",
                    title=term.canonical_title,
                    description=term.description,
                    status=status,
                    generated=ActorInfo(by="wikid-steward/compiler"),
                    sources=concept_sources,
                    tags=["concept", profile.name],
                    custom_metadata={"aliases": term.aliases},
                )
                if reviewer:
                    concept_doc.verified = [VerifiedEntry(by=reviewer)]

                c_fm = generate_okf_v7_frontmatter(concept_doc)
                c_body = (
                    f"# {term.canonical_title}\n\n"
                    f"## 概要\n{term.description}\n\n"
                    f"## 別名・表記揺れ\n"
                    + "\n".join([f"- {alias}" for alias in term.aliases])
                    + f"\n\n{HUMAN_MEMO_TEMPLATE}"
                )

                final_c_content = merge_human_memo(f"{c_fm}\n{c_body}", existing_content)
                concept_note_path.write_text(final_c_content, encoding="utf-8")
                concept_paths.append(concept_note_path)

        # 6. メイン構造化Wikiノートの生成
        handler = get_profile_handler(profile.name)
        processed_md = handler.post_process_markdown(raw_extracted_text, profile.name)

        # 画像リンク置換
        processed_md = replace_image_links(
            processed_md, slug, extracted_image_names=extracted_image_names
        )

        # 用語の WikiRelinker 適用（抽出用語または既存用語で [[WikiLink]] 化）
        if extracted_terms:
            relinker = WikiRelinker(stop_words=set(self.config.relinker.stop_words))
            processed_md, _ = relinker.relink_text(
                processed_md,
                extracted_terms,
                mode=self.config.relinker.mode,
            )

        # 手書きメモ保護とセクション付加
        main_note_path = wiki_dir / f"{slug}.md"
        existing_main_content = (
            main_note_path.read_text(encoding="utf-8")
            if main_note_path.exists()
            else None
        )

        main_sources = []
        if source_resource_path or not hide_source_links:
            main_sources.append(
                SourceEntry(
                    id="source",
                    resource=source_resource_path,
                    title=title,
                )
            )

        main_okf_doc = OKFDocumentData(
            doc_type=profile.doc_type,
            title=title,
            description=f"Structured knowledge note extracted from {path.name}",
            status=status,
            generated=ActorInfo(by="wikid-steward/compiler"),
            sources=main_sources,
            tags=[profile.name, "compiled"],
            custom_metadata=custom_meta,
        )
        if reviewer:
            main_okf_doc.verified = [VerifiedEntry(by=reviewer)]

        main_fm_str = generate_okf_v7_frontmatter(main_okf_doc)
        main_body_with_memo = (
            f"{processed_md}\n\n{HUMAN_MEMO_TEMPLATE}"
            if "## 📝 手書きメモ" not in processed_md
            else processed_md
        )

        final_main_content = merge_human_memo(
            f"{main_fm_str}\n{main_body_with_memo}", existing_main_content
        )
        main_note_path.write_text(final_main_content, encoding="utf-8")

        return CompilationResult(
            raw_markdown_path=raw_markdown_path,
            main_note_path=main_note_path,
            concept_note_paths=concept_paths,
            extracted_images=extracted_image_paths,
            saved_source_path=saved_source_path,
        )

    def compile_directory(
        self,
        dir_path: Path | str,
        output_dir: Path | None = None,
        status: str = "draft",
        reviewer: str | None = None,
        save_source: bool = True,
        hide_source_links: bool = False,
        extract_terms: bool = True,
        profile_name: str | None = None,
    ) -> list[CompilationResult]:
        """ディレクトリ内のドキュメント群を一括コンパイルする。"""
        target_dir = Path(dir_path)
        if not target_dir.is_absolute():
            target_dir = self.base_dir / target_dir

        if not target_dir.exists() or not target_dir.is_dir():
            raise NotADirectoryError(f"Directory not found: {target_dir}")

        supported_exts = [
            ".pdf",
            ".docx",
            ".pptx",
            ".xlsx",
            ".md",
            ".txt",
            ".html",
        ]
        results = []
        for file_p in sorted(target_dir.rglob("*")):
            if file_p.is_file() and file_p.suffix.lower() in supported_exts:
                # _raw, wiki, .git などの中間/出力ディレクトリは除外
                if any(
                    part in [".git", "_raw", "wiki", "staging", "assets"]
                    for part in file_p.parts
                ):
                    continue
                try:
                    res = self.compile_file(
                        file_path=file_p,
                        output_dir=output_dir,
                        status=status,
                        reviewer=reviewer,
                        save_source=save_source,
                        hide_source_links=hide_source_links,
                        extract_terms=extract_terms,
                        profile_name=profile_name,
                    )
                    results.append(res)
                except Exception as e:
                    logger.error(f"Failed to compile {file_p}: {e}")

        return results

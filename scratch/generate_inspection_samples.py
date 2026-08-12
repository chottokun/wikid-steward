from pathlib import Path
from wikid_steward.core.handlers import get_profile_handler
from wikid_steward.core.metadata_embedder import embed_png_metadata, prepare_clean_assets_dir, read_png_metadata
from wikid_steward.core.okf_converter import generate_okf_frontmatter, replace_image_links
from wikid_steward.core.parser import KnowledgeParser
from wikid_steward.core.profiles import resolve_profile
from wikid_steward.core.slug import generate_slug


def generate_real_inspection_samples_with_assets():
    base_dir = Path.cwd()
    output_dir = base_dir / "test_output" / "inspection"
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list((base_dir / "raw_sources").glob("**/*.pdf")) + list((base_dir / "_raw").glob("**/*.pdf"))
    parser = KnowledgeParser()

    print(f"Found {len(pdf_files)} PDF files for asset inspection.")

    for raw_file in pdf_files:
        try:
            rel_path = raw_file.relative_to(base_dir / "raw_sources")
        except ValueError:
            rel_path = raw_file.relative_to(base_dir / "_raw")

        profile, prof_source, custom_meta = resolve_profile(raw_file, base_dir / "raw_sources")
        slug = generate_slug(str(rel_path.with_suffix("")))

        print(f"\n[Processing] {raw_file.name} -> {slug}")

        # 1. Docling パースの実行
        conv_result = parser.parse(raw_file, profile=profile)
        raw_md = conv_result.document.export_to_markdown()

        # 2. アセット切出 ＆ 【層B】 PNG メタデータ埋め込み
        assets_dir = prepare_clean_assets_dir(output_dir / "assets" / slug)
        extracted_image_names = []

        if hasattr(conv_result.document, "pictures"):
            for i, pic in enumerate(conv_result.document.pictures):
                if hasattr(pic, "image") and pic.image:
                    img_name = f"fig{i + 1}.png"
                    img_path = assets_dir / img_name
                    pic.image.pil_image.save(img_path)

                    meta_payload = {
                        "uuid": f"img_{slug}_crop{i + 1:02d}",
                        "parent_doc_id": slug,
                        "original_source": f"raw_sources/{rel_path}",
                        "page_number": getattr(pic, "page_no", 1),
                        "extracted_by": "Docling v2.x & wikid-steward",
                    }
                    embed_png_metadata(img_path, meta_payload)
                    extracted_image_names.append(img_name)

        print(f"  -> Extracted {len(extracted_image_names)} figures to {assets_dir}")

        # 3. ハンドラー後処理 ＆ OKF Frontmatter
        handler = get_profile_handler(profile.name)
        processed_md = handler.post_process_markdown(raw_md, profile.name)

        frontmatter = generate_okf_frontmatter(
            doc_id=slug,
            title=raw_file.stem,
            doc_type=profile.doc_type,
            source_path=f"raw_sources/{rel_path}",
            profile_used=profile.name,
            profile_source=prof_source,
            custom_metadata=custom_meta,
        )
        body = replace_image_links(
            processed_md, slug, extracted_image_names=extracted_image_names
        )
        final_markdown = f"{frontmatter}\n{body}"

        out_file = output_dir / f"{slug}.md"
        out_file.write_text(final_markdown, encoding="utf-8")

if __name__ == "__main__":
    generate_real_inspection_samples_with_assets()

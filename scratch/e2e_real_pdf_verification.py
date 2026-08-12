from pathlib import Path
from wikid_steward.core.handlers import get_profile_handler
from wikid_steward.core.metadata_embedder import embed_png_metadata, prepare_clean_assets_dir, read_png_metadata
from wikid_steward.core.okf_converter import generate_okf_frontmatter, replace_image_links
from wikid_steward.core.parser import KnowledgeParser
from wikid_steward.core.profiles import resolve_profile
from wikid_steward.core.slug import generate_slug


def verify_real_pdf_ingest():
    base_dir = Path.cwd()
    out_dir = base_dir / "test_output" / "e2e_real_pdf_check"
    out_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list((base_dir / "raw_sources").glob("**/*.pdf"))
    if not pdf_files:
        print("ERROR: No real PDF files found in raw_sources/")
        return

    parser = KnowledgeParser()

    print(f"=== E2E Inspection for {len(pdf_files)} Real PDFs ===")

    for raw_file in pdf_files:
        try:
            rel_path = raw_file.relative_to(base_dir / "raw_sources")
        except ValueError:
            rel_path = raw_file.relative_to(base_dir / "_raw")

        profile, prof_source, custom_meta = resolve_profile(raw_file, base_dir / "raw_sources")
        slug = generate_slug(str(rel_path.with_suffix("")))

        print(f"\n--------------------------------------------------")
        print(f"📄 Processing Real PDF: {raw_file.name}")
        print(f"   Slug: {slug} | Profile: {profile.name} ({prof_source})")

        # 1. パース実行
        conv_result = parser.parse(raw_file, profile=profile)
        raw_md = conv_result.document.export_to_markdown()

        # 2. 画像アセット切り出し & 【層B】メタデータ焼き込み
        assets_dir = prepare_clean_assets_dir(out_dir / "assets" / slug)
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
                        "extracted_by": "docling-lib 58fc69c & wikid-steward",
                    }
                    embed_png_metadata(img_path, meta_payload)
                    extracted_image_names.append(img_name)

        print(f"   📷 Extracted {len(extracted_image_names)} figures to: {assets_dir}")

        # 3. ハンドラー後処理 ＆ OKF 【層A】 Header ＆ 画像タグ置換
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

        out_md_path = out_dir / f"{slug}.md"
        out_md_path.write_text(final_markdown, encoding="utf-8")

        # --- 狙い通りの結果チェック ---
        print(f"   CHECK 1 [OKF Header]: {'PASS' if 'profile_used:' in frontmatter else 'FAIL'}")
        print(f"   CHECK 2 [Image Tags]: {'PASS' if f'![[assets/{slug}/' in body else 'FAIL'}")
        print(f"   CHECK 3 [Content Size]: {len(final_markdown.splitlines())} lines ({len(final_markdown)} bytes)")

        if extracted_image_names:
            first_img = assets_dir / extracted_image_names[0]
            read_meta = read_png_metadata(first_img)
            print(f"   CHECK 4 [Layer B PNG Metadata]: {'PASS' if read_meta.get('parent_doc_id') == slug else 'FAIL'}")
            print(f"            Sample Metadata: {read_meta}")

if __name__ == "__main__":
    verify_real_pdf_ingest()

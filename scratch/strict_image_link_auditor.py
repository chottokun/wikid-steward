from pathlib import Path
import re
from wikid_steward.core.handlers import get_profile_handler
from wikid_steward.core.metadata_embedder import embed_png_metadata, prepare_clean_assets_dir, read_png_metadata
from wikid_steward.core.okf_converter import generate_okf_frontmatter, replace_image_links
from wikid_steward.core.parser import KnowledgeParser
from wikid_steward.core.profiles import resolve_profile
from wikid_steward.core.slug import generate_slug


def audit_all_image_links():
    base_dir = Path.cwd()
    out_dir = base_dir / "test_output" / "strict_audit"
    out_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list((base_dir / "raw_sources").glob("**/*.pdf"))
    if not pdf_files:
        print("ERROR: No real PDF files found in raw_sources/")
        return

    parser = KnowledgeParser()

    print("==========================================================================")
    print("      🔍 STRICT IMAGE LINK & FILE EXISTENCE AUDIT REPORT")
    print("==========================================================================")

    total_images_checked = 0
    total_images_valid = 0

    for raw_file in pdf_files:
        try:
            rel_path = raw_file.relative_to(base_dir / "raw_sources")
        except ValueError:
            rel_path = raw_file.relative_to(base_dir / "_raw")

        profile, prof_source, custom_meta = resolve_profile(raw_file, base_dir / "raw_sources")
        slug = generate_slug(str(rel_path.with_suffix("")))

        print(f"\n📄 Document: {raw_file.name}")
        print(f"   Slug: {slug}")

        # 1. パース実行
        conv_result = parser.parse(raw_file, profile=profile)
        raw_md = conv_result.document.export_to_markdown()

        # 2. 画像切出 & メタデータ埋め込み
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
                    }
                    embed_png_metadata(img_path, meta_payload)
                    extracted_image_names.append(img_name)

        # 3. ハンドラー後処理 & OKF Header 付与
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

        # 4. 画像リンクの厳密存在走査
        image_matches = re.findall(r"\!\[(.*?)\]\((.*?)\)", final_markdown)

        print(f"   📷 Found {len(image_matches)} image tags in Markdown.")

        for alt, img_rel_link in image_matches:
            total_images_checked += 1
            # Markdown ファイルからの相対パス判定
            target_file_path = (out_dir / img_rel_link).resolve()
            exists = target_file_path.exists() and target_file_path.is_file()

            if exists:
                total_images_valid += 1
                file_bytes = target_file_path.stat().st_size
                layer_b_meta = read_png_metadata(target_file_path)
                print(f"   [VALID LINK ✅] Tag: ![{alt}]({img_rel_link})")
                print(f"                   -> Disk Path: {target_file_path}")
                print(f"                   -> Size: {file_bytes} bytes | Layer B uuid: {layer_b_meta.get('uuid')}")
            else:
                print(f"   [BROKEN LINK ❌] Tag: ![{alt}]({img_rel_link})")
                print(f"                    -> MISSING at: {target_file_path}")

    print("\n==========================================================================")
    print(f"📊 AUDIT RESULT: {total_images_valid} / {total_images_checked} Image Links Valid.")
    print(f"   Status: {'ALL PASSED - 0 BROKEN LINKS 🎉' if total_images_valid == total_images_checked and total_images_checked > 0 else 'AUDIT FAILED'}")
    print("==========================================================================")

if __name__ == "__main__":
    audit_all_image_links()

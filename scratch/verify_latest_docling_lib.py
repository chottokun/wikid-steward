from pathlib import Path
from wikid_steward.core.okf_converter import replace_image_links
from docling_lib import EnhancedDoclingConverter, PDFConverter, DocumentConversionOptions

def verify_strict_image_paths():
    pdf_path = Path("raw_sources/llm/LLM-as-a-Judge.pdf")
    slug = "llm_llm-as-a-judge"

    out_dir = Path("test_output/strict_check")
    assets_dir = out_dir / "assets" / slug
    assets_dir.mkdir(parents=True, exist_ok=True)

    options = DocumentConversionOptions(do_ocr=False, image_scale=2.0)
    pdf_converter = PDFConverter(options=options)
    enhanced_converter = EnhancedDoclingConverter(docling_converter=pdf_converter)

    print(f"Parsing {pdf_path.name}...")
    raw_md = enhanced_converter.convert_to_markdown(
        input_path=pdf_path,
        assets_dir=assets_dir
    )

    # okf_converter による 決定論的 slug パスへの完全アラインメント
    final_md = replace_image_links(raw_md, slug)

    out_md = out_dir / f"{slug}.md"
    out_md.write_text(final_md, encoding="utf-8")

    print("\n--- Image Link Verification Results ---")
    tag_lines = [line for line in final_md.splitlines() if "![" in line]
    
    all_links_valid = True
    for line in tag_lines:
        print(f"Tag Line: {line}")
        # 画像パスの抽出 (例: assets/llm_llm-as-a-judge/picture_1.png)
        if "(" in line and ")" in line:
            rel_img_path = line.split("(")[1].split(")")[0]
            abs_img_path = out_dir / rel_img_path
            exists = abs_img_path.exists()
            print(f"  -> Target Image Path: {rel_img_path}")
            print(f"  -> File Exists on Disk: {'YES (Valid Link)' if exists else 'NO (Broken Link)'}")
            if not exists:
                all_links_valid = False

    print(f"\nFinal Verification Status: {'SUCCESS - All Image Links Valid!' if all_links_valid else 'FAILURE - Broken Links Found!'}")

if __name__ == "__main__":
    verify_strict_image_paths()

from pathlib import Path
from docling_lib import EnhancedDoclingConverter, PDFConverter, DocumentConversionOptions

def test_fixed_docling_lib_slug_alignment():
    pdf_path = Path("raw_sources/llm/LLM-as-a-Judge.pdf")
    slug = "llm_llm-as-a-judge"

    out_dir = Path("test_output/fixed_lib_check")
    assets_dir = out_dir / "assets" / slug
    assets_dir.mkdir(parents=True, exist_ok=True)

    options = DocumentConversionOptions(do_ocr=False, image_scale=2.0)
    pdf_converter = PDFConverter(options=options)
    enhanced_converter = EnhancedDoclingConverter(docling_converter=pdf_converter)

    print(f"Parsing {pdf_path.name} with slug='{slug}'...")

    # 1. 決定論的 slug を指定してライブラリで直接パース
    md_result = enhanced_converter.convert_to_markdown(
        input_path=pdf_path,
        slug=slug,
        assets_dir=assets_dir
    )

    out_file = out_dir / f"{slug}.md"
    out_file.write_text(md_result, encoding="utf-8")

    print(f"\n✅ Conversion Successful!")
    print(f"File Saved: {out_file}")

    # 2. 生成された画像タグとディスク上の保存ファイルの完全一致チェック
    lines = md_result.splitlines()
    tag_lines = [line for line in lines if "![" in line]

    print(f"\n--- Checking Image Link Integrity ---")
    all_valid = True
    for line in tag_lines:
        print(f"Tag Line: {line}")
        if "(" in line and ")" in line:
            rel_img_path = line.split("(")[1].split(")")[0]
            abs_img_path = out_dir / rel_img_path
            exists = abs_img_path.exists()
            print(f"  -> Path: {rel_img_path}")
            print(f"  -> File Exists: {'YES (Valid Link)' if exists else 'NO (Broken Link)'}")
            if not exists:
                all_valid = False

    print(f"\nFinal Library Verification Status: {'SUCCESS - 100% Valid Links!' if all_valid else 'FAILURE'}")

if __name__ == "__main__":
    test_fixed_docling_lib_slug_alignment()

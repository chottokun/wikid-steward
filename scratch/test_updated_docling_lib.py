from pathlib import Path
from docling_lib import EnhancedDoclingConverter, PDFConverter, DocumentConversionOptions

options = DocumentConversionOptions(do_ocr=False, image_scale=2.0)
pdf_converter = PDFConverter(options=options)
enhanced_converter = EnhancedDoclingConverter(docling_converter=pdf_converter)

pdf_file = Path("raw_sources/llm/LLM-as-a-Judge.pdf")
if pdf_file.exists():
    md_output = enhanced_converter.convert_to_markdown(
        input_path=pdf_file,
        image_tag_template="![[assets/llm_llm-as-a-judge/{image_name}]]",
        assets_dir=Path("test_output/new_assets/llm_llm-as-a-judge")
    )

    print(f"Successfully converted {pdf_file.name} to Markdown!")
    print(f"Output lines: {len(md_output.splitlines())}, Bytes: {len(md_output)}")
    print("\n--- First 30 lines ---")
    print("\n".join(md_output.splitlines()[:30]))

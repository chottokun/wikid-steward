from pathlib import Path
from docling_lib import EnhancedDoclingConverter, PDFConverter, DocumentConversionOptions


def test_vlm_real_ollama():
    pdf_path = Path("raw_sources/llm/LLM-as-a-Judge.pdf")
    slug = "llm_llm-as-a-judge_vlm_real"

    out_dir = Path("test_output/vlm_real_check")
    assets_dir = out_dir / "assets" / slug
    assets_dir.mkdir(parents=True, exist_ok=True)

    print("=== Testing Real Ollama VLM Execution ===")
    print("Using model: qwen3.5:4b")

    # インストール済みモデル qwen3.5:4b を指定
    options = DocumentConversionOptions(
        do_ocr=False,
        image_scale=2.0,
        vlm_enabled=True,
        vlm_provider="ollama",
        vlm_model="qwen3.5:4b",
        vlm_endpoint="http://localhost:11434",
        vlm_prompt="この画像の概要を1〜2文程度で簡潔に日本語で説明してください。"
    )

    pdf_converter = PDFConverter(options=options)
    enhanced_converter = EnhancedDoclingConverter(docling_converter=pdf_converter)

    try:
        print(f"Parsing {pdf_path.name} with Ollama (qwen3.5:4b)...")
        md_result = enhanced_converter.convert_to_markdown(
            input_path=pdf_path,
            slug=slug,
            assets_dir=assets_dir
        )

        out_file = out_dir / f"{slug}.md"
        out_file.write_text(md_result, encoding="utf-8")

        print("\n✅ VLM Ollama Execution Completed Successfully!")
        print(f"File Saved: {out_file}")
        print(f"Lines: {len(md_result.splitlines())}, Bytes: {len(md_result)}")

        # 画像タグおよびVLM生成テキスト周辺の出力確認
        lines = md_result.splitlines()
        print("\n📷 Generated Image Tags & Captions:")
        for i, line in enumerate(lines):
            if "![" in line or "画像" in line or "Figure" in line:
                print(f"Line {i+1}: {line}")

    except Exception as e:
        print(f"\n⚠️ Ollama Execution Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vlm_real_ollama()

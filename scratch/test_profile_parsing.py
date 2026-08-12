from pathlib import Path
from wikid_steward.core.parser import KnowledgeParser
from wikid_steward.core.profiles import resolve_profile


def test_drawing_vs_paper_parsing():
    base_dir = Path.cwd()
    test_output_dir = base_dir / "test_output" / "profile_experiment"
    test_output_dir.mkdir(parents=True, exist_ok=True)

    # 仮想的な _raw ディレクトリ構成
    raw_drawings = base_dir / "_raw" / "drawings" / "sample_dwg.pdf"
    raw_papers = base_dir / "_raw" / "papers" / "sample_paper.pdf"

    # プロファイル解決のテスト
    drawing_profile, draw_src, _ = resolve_profile(
        raw_drawings, base_dir / "_raw"
    )
    paper_profile, paper_src, _ = resolve_profile(raw_papers, base_dir / "_raw")

    print("=== Profile Resolution Results ===")
    print(
        f"Drawing Path: {raw_drawings.relative_to(base_dir)} -> Profile: {drawing_profile.name} (Source: {draw_src}), OCR: {drawing_profile.do_ocr}, Scale: {drawing_profile.images_scale}"
    )
    print(
        f"Paper Path:   {raw_papers.relative_to(base_dir)} -> Profile: {paper_profile.name} (Source: {paper_src}), OCR: {paper_profile.do_ocr}, Scale: {paper_profile.images_scale}"
    )

    assert drawing_profile.name == "drawing"
    assert drawing_profile.do_ocr is True
    assert drawing_profile.images_scale == 3.0

    assert paper_profile.name == "paper"
    assert paper_profile.do_ocr is False
    assert paper_profile.images_scale == 2.0

    print(
        "\n✅ Directory policy profile resolution verified successfully for drawing & paper!"
    )


if __name__ == "__main__":
    test_drawing_vs_paper_parsing()

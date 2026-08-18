from pathlib import Path

from wikid_steward.core.okf_converter import generate_okf_frontmatter
from wikid_steward.core.profiles import resolve_profile
from wikid_steward.core.slug import generate_slug


def test_directory_policy_drawing_resolution(tmp_path: Path):
    """_raw/drawings/ 配下に図面 PDF が置かれた際、directory_policy により drawing プロファイルが選ばれる結合テスト"""
    base_raw = tmp_path / "_raw"
    drawings_dir = base_raw / "drawings"
    drawings_dir.mkdir(parents=True)

    # ダミーの PDF ファイルを作成
    drawing_pdf = drawings_dir / "DWG-2026-X88.pdf"
    drawing_pdf.write_bytes(b"%PDF-1.4 dummy pdf content for drawing test")

    # 1. プロファイル解決のテスト
    profile, source, custom_meta = resolve_profile(drawing_pdf, base_raw)

    assert profile.name == "drawing"
    assert profile.doc_type == "Technical Drawing"
    assert profile.do_ocr is True
    assert profile.images_scale == 3.0
    assert source == "directory_policy"

    # 2. OKF Frontmatter へのトレーサビリティ出力テスト
    slug = generate_slug("drawings/DWG-2026-X88")
    frontmatter = generate_okf_frontmatter(
        doc_id=slug,
        title=drawing_pdf.stem,
        doc_type=profile.doc_type,
        source_path=f"raw_sources/drawings/{drawing_pdf.name}",
        profile_used=profile.name,
        profile_source=source,
    )

    assert "type: Technical Drawing" in frontmatter
    assert "profile_used: drawing" in frontmatter
    assert "profile_source: directory_policy" in frontmatter


def test_directory_policy_paper_resolution(tmp_path: Path):
    """_raw/papers/ 配下に論文 PDF が置かれた際、directory_policy により paper プロファイルが選ばれる結合テスト"""
    base_raw = tmp_path / "_raw"
    papers_dir = base_raw / "papers"
    papers_dir.mkdir(parents=True)

    paper_pdf = papers_dir / "arxiv_paper.pdf"
    paper_pdf.write_bytes(b"%PDF-1.4 dummy pdf content for paper test")

    profile, source, custom_meta = resolve_profile(paper_pdf, base_raw)

    assert profile.name == "paper"
    assert profile.doc_type == "Academic Paper"
    assert profile.do_ocr is False
    assert profile.images_scale == 2.0
    assert source == "directory_policy"

    slug = generate_slug("papers/arxiv_paper")
    frontmatter = generate_okf_frontmatter(
        doc_id=slug,
        title=paper_pdf.stem,
        doc_type=profile.doc_type,
        source_path=f"raw_sources/papers/{paper_pdf.name}",
        profile_used=profile.name,
        profile_source=source,
    )

    assert "type: Academic Paper" in frontmatter
    assert "profile_used: paper" in frontmatter
    assert "profile_source: directory_policy" in frontmatter


def test_default_fallback_resolution(tmp_path: Path):
    """特定キーワードが含まれない _raw/unknown/ 配下の場合、default により paper プロファイルが選ばれる結合テスト"""
    base_raw = tmp_path / "_raw"
    unknown_dir = base_raw / "unknown"
    unknown_dir.mkdir(parents=True)

    general_pdf = unknown_dir / "general_memo.pdf"
    general_pdf.write_bytes(b"%PDF-1.4 dummy pdf content for general test")

    profile, source, custom_meta = resolve_profile(general_pdf, base_raw)

    assert profile.name == "paper"
    assert source == "default"

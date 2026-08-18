from pathlib import Path

import pytest

from wikid_steward.core.okf_converter import parse_okf_frontmatter
from wikid_steward.core.promoter import promote_document
from wikid_steward.watcher.daemon import RawFolderHandler


@pytest.mark.slow
def test_arxiv_real_pdf_ingest_pipeline(tmp_path: Path):
    """実際の ArXiv PDF (LoRA / RAG) を _raw に投入し、

    _raw/ -> staging/ -> wiki/ (OKF v0.2 Markdown + assets/{slug}/) の全パイプラインを検証する。
    """
    project_root = Path.cwd()
    lora_pdf = project_root / "raw_sources" / "finetuning" / "LoRA-Low-Rank-Adaptation.pdf"
    if not lora_pdf.exists():
        pytest.skip("LoRA PDF not found")

    base_raw = tmp_path / "_raw"
    base_staging = tmp_path / "staging"
    base_wiki = tmp_path / "wiki"
    base_raw_sources = tmp_path / "raw_sources"

    base_raw.mkdir(parents=True)
    base_staging.mkdir(parents=True)
    base_wiki.mkdir(parents=True)
    base_raw_sources.mkdir(parents=True)

    # 1. _raw/finetuning/ 配下に原本 PDF を配置
    target_raw_dir = base_raw / "finetuning"
    target_raw_dir.mkdir(parents=True)
    test_pdf = target_raw_dir / "LoRA-Low-Rank-Adaptation.pdf"
    test_pdf.write_bytes(lora_pdf.read_bytes())

    # 2. RawFolderHandler によるステージング抽出
    raw_handler = RawFolderHandler(tmp_path)
    raw_handler._process_raw_file(test_pdf)

    # staging/ 配下に Markdown と assets が生成されたか検証
    staging_mds = list(base_staging.glob("**/*.md"))
    assert len(staging_mds) == 1, "Staging markdown should be created"
    staging_md = staging_mds[0]

    staging_content = staging_md.read_text(encoding="utf-8")
    fm, body = parse_okf_frontmatter(staging_content)

    assert fm.get("type") in ("Academic Paper", "General Document", "Concept")
    assert "LoRA" in staging_content or "Low-Rank" in staging_content

    # 3. promote_document による wiki/ 本番昇格
    promote_document(
        staging_note=staging_md,
        base_dir=tmp_path,
        raw_relative_path=Path("finetuning/LoRA-Low-Rank-Adaptation.pdf"),
        commit_git=False,
    )

    # wiki/ 配下にメインノートおよび用語ノートが昇格されたか検証
    main_paper_notes = list((base_wiki / "finetuning").glob("*.md"))
    assert len(main_paper_notes) >= 1, "Main paper note in wiki/finetuning/ should be promoted"
    promoted_note = main_paper_notes[0]
    assert promoted_note.exists()

    wiki_content = promoted_note.read_text(encoding="utf-8")
    w_fm, w_body = parse_okf_frontmatter(wiki_content)

    assert w_fm.get("type") is not None
    assert "LoRA" in wiki_content or "Low-Rank" in wiki_content

    # 用語ノート (wiki/glossary/) が自動抽出・作成されているか検証
    glossary_notes = list((base_wiki / "glossary").glob("*.md"))
    assert len(glossary_notes) >= 1, "Glossary notes should be auto-extracted"

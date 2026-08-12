from pathlib import Path
import time
from wikid_steward.core.metadata_embedder import (
    embed_png_metadata,
    prepare_clean_assets_dir,
    read_png_metadata,
)
from wikid_steward.core.okf_converter import (
    generate_okf_frontmatter,
    replace_image_links,
)
from wikid_steward.core.parser import KnowledgeParser
from wikid_steward.core.promoter import promote_document
from wikid_steward.core.slug import generate_slug


def run_experiment():
    base_dir = Path.cwd()
    raw_dir = base_dir / "_raw"
    staging_dir = base_dir / "staging"
    wiki_dir = base_dir / "wiki"
    raw_sources_dir = base_dir / "raw_sources"

    parser = KnowledgeParser()

    pdf_files = list(raw_dir.glob("**/*.pdf"))
    print(f"=== [STEP 1] Found {len(pdf_files)} raw PDF files ===")

    staged_notes = []

    # --- インジェストフェーズ ---
    for pdf_path in pdf_files:
        rel_path = pdf_path.relative_to(raw_dir)
        rel_no_ext = str(rel_path.with_suffix(""))
        slug = generate_slug(rel_no_ext)

        print(f"\nProcessing: {rel_path} -> Slug: {slug}")

        # 1. Docling パース
        start_t = time.time()
        conv_result = parser.parse(pdf_path)
        doc_md = conv_result.document.export_to_markdown()
        elapsed = time.time() - start_t
        print(f"  Parsed in {elapsed:.2f}s")

        # 2. アセット出力と 【層B】 PNG メタデータ埋め込み
        staging_note_dir = staging_dir / rel_path.parent
        staging_assets_dir = prepare_clean_assets_dir(
            staging_note_dir / "assets" / slug
        )

        extracted_pics = 0
        if hasattr(conv_result.document, "pictures"):
            for i, pic in enumerate(conv_result.document.pictures):
                if hasattr(pic, "image") and pic.image:
                    img_name = f"fig{i + 1}.png"
                    img_path = staging_assets_dir / img_name
                    pic.image.pil_image.save(img_path)

                    meta_payload = {
                        "uuid": f"img_{slug}_crop{i + 1:02d}",
                        "parent_doc_id": slug,
                        "original_source": str(Path("raw_sources") / rel_path),
                        "page_number": getattr(pic, "page_no", 1),
                    }
                    embed_png_metadata(img_path, meta_payload)
                    extracted_pics += 1

        print(
            f"  Extracted {extracted_pics} figure images to {staging_assets_dir}"
        )

        # 【層B】埋め込みの読み戻し検証
        if extracted_pics > 0:
            sample_img = staging_assets_dir / "fig1.png"
            read_meta = read_png_metadata(sample_img)
            print(
                f"  [Layer B Verification] Read metadata from fig1.png: parent={read_meta.get('parent_doc_id')}"
            )

        # 3. OKF 【層A】 Frontmatter 付与 & Markdown 画像パス置換
        frontmatter = generate_okf_frontmatter(
            doc_id=slug,
            title=pdf_path.stem,
            doc_type="Academic Paper",
            source_path=str(Path("raw_sources") / rel_path),
            tags=["arxiv", rel_path.parent.name],
        )
        body = replace_image_links(doc_md, slug)
        final_content = f"{frontmatter}\n{body}"

        # 4. staging/ への配置
        staging_note = staging_note_dir / f"{slug}.md"
        staging_note_dir.mkdir(parents=True, exist_ok=True)
        staging_note.write_text(final_content, encoding="utf-8")
        print(f"  Saved staging note: {staging_note}")
        staged_notes.append((staging_note, rel_path))

    # --- レビュー ＆ 昇格フェーズ (HITL シミュレーション) ---
    print("\n=== [STEP 2] Simulating Human Review (status: reviewed) & Promotion ===")

    for staging_note, rel_path in staged_notes:
        # ノートの status を unreviewed から reviewed に書き換え
        content = staging_note.read_text(encoding="utf-8")
        reviewed_content = content.replace(
            'status: "unreviewed"', 'status: "reviewed"'
        ).replace("status: unreviewed", "status: reviewed")
        staging_note.write_text(reviewed_content, encoding="utf-8")

        # 昇格の実行
        promote_document(
            staging_note=staging_note,
            base_dir=base_dir,
            raw_relative_path=rel_path,
            commit_git=False,
        )
        print(f"Promoted: {staging_note.name} -> wiki/")

    print("\n=== [STEP 3] Verification of final 4-layer file locations ===")
    print(f"Staging files count: {len(list(staging_dir.glob('**/*.md')))}")
    print(f"Wiki markdown files count: {len(list(wiki_dir.glob('**/*.md')))}")
    print(
        f"Raw sources archived files count: {len(list(raw_sources_dir.glob('**/*.pdf')))}"
    )

    print("\nGenerated Wiki Files:")
    for w in wiki_dir.glob("**/*.md"):
        print(f" - {w.relative_to(base_dir)}")


if __name__ == "__main__":
    run_experiment()

import gc
from pathlib import Path
import shutil

from wikid_steward.core.glossary import GlossaryExtractor
from wikid_steward.core.linter import KnowledgeLinter
from wikid_steward.core.metadata_embedder import prepare_clean_assets_dir
from wikid_steward.core.moc_generator import generate_all_mocs
from wikid_steward.core.okf_converter import generate_okf_frontmatter, replace_image_links
from wikid_steward.core.parser import KnowledgeParser
from wikid_steward.core.profiles import ParseProfile
from wikid_steward.core.promoter import promote_document
from wikid_steward.core.slug import generate_slug
from wikid_steward.vector.indexer import (
    OpenAICompatibleEmbeddingClient,
    QdrantKnowledgeIndexer,
)
from wikid_steward.vector.searcher import WikiGraphSearchEngine


def run_ollama_qwen_embedding_audit():
    print("==========================================================================")
    print("      🚀 OLLAMA QWEN3-EMBEDDING:0.6B HIGH-PERFORMANCE AUDIT")
    print("==========================================================================")

    base_dir = Path.cwd()
    audit_root = base_dir / "test_output" / "multi_arxiv_audit"
    if audit_root.exists():
        shutil.rmtree(audit_root)

    audit_root.mkdir(parents=True, exist_ok=True)
    raw_base = audit_root / "_raw"
    staging_base = audit_root / "staging"
    wiki_base = audit_root / "wiki"

    # 対象の論文 PDF 一覧
    pdf_sources = list((base_dir / "raw_sources").glob("**/*.pdf"))
    print(f"[Step 0] Found {len(pdf_sources)} real arXiv PDFs to process.")

    parser = KnowledgeParser()
    light_profile = ParseProfile(
        name="paper_light",
        doc_type="Academic Paper",
        do_ocr=False,
        vlm_enabled=False,
    )

    for idx, pdf_file in enumerate(pdf_sources, 1):
        rel_sub = pdf_file.parent.name
        (raw_base / rel_sub).mkdir(parents=True, exist_ok=True)
        (staging_base / rel_sub).mkdir(parents=True, exist_ok=True)

        target_raw_pdf = raw_base / rel_sub / pdf_file.name
        shutil.copy(pdf_file, target_raw_pdf)

        print(f"\n[Step 1.{idx}] Processing: {pdf_file.name} (Category: {rel_sub})")
        slug = generate_slug(f"{rel_sub}/{pdf_file.stem}")

        print(f"  -> Parsing PDF with Docling...")
        conv_res = parser.parse(target_raw_pdf, profile=light_profile)
        raw_md = conv_res.document.export_to_markdown()

        assets_dir = prepare_clean_assets_dir(staging_base / rel_sub / "assets" / slug)
        img_names = []
        if hasattr(conv_res.document, "pictures"):
            for i, pic in enumerate(conv_res.document.pictures):
                if hasattr(pic, "image") and pic.image:
                    iname = f"fig{i+1}.png"
                    pic.image.pil_image.save(assets_dir / iname)
                    img_names.append(iname)

        frontmatter = generate_okf_frontmatter(
            doc_id=slug,
            title=pdf_file.stem,
            doc_type=light_profile.doc_type,
            source_path=f"raw_sources/{rel_sub}/{pdf_file.name}",
            custom_metadata={"status": "reviewed"},
        )
        body = replace_image_links(raw_md, slug, extracted_image_names=img_names)
        staging_note = staging_base / rel_sub / f"{pdf_file.stem}.md"
        staging_note.write_text(f"{frontmatter}\n{body}", encoding="utf-8")

        print(f"  -> Saved Staging Note: {staging_note.name} ({len(img_names)} images)")

        # 昇格
        print("  -> Promoting to Wiki Vault & Extracting Glossary Terms...")
        promote_document(
            staging_note=staging_note,
            base_dir=audit_root,
            raw_relative_path=Path(rel_sub) / pdf_file.name,
            commit_git=False,
        )

        del conv_res, raw_md
        gc.collect()

    # Step 2: MOC 自動生成
    print("\n[Step 2] Generating Dynamic Maps of Content (MOCs)...")
    mocs = generate_all_mocs(wiki_base)
    print(f"  -> Generated {len(mocs)} MOC index files.")

    # Step 3: Linter 健全性監査
    print("\n[Step 3] Running Self-Healing Knowledge Linter...")
    linter = KnowledgeLinter(wiki_base)
    report = linter.run_lint()

    print(f"  -> Total Files Scanned: {report.total_files}")
    print(f"  -> Health Audit Result: {'100% HEALTHY 🎉' if report.is_healthy else 'ISSUES FOUND ❌'}")

    # Step 4: Qdrant ベクトルインデックス (Ollama qwen3-embedding:0.6b)
    print("\n[Step 4] Building Qdrant Vector Index via Ollama 'qwen3-embedding:0.6b'...")
    ollama_embed_client = OpenAICompatibleEmbeddingClient(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        model="qwen3-embedding:0.6b",
    )
    indexer = QdrantKnowledgeIndexer(
        location=":memory:", embedding_client=ollama_embed_client
    )
    indexed_cnt = indexer.index_wiki_directory(wiki_base)
    print(f"  -> Total Qdrant Indexed Points: {indexed_cnt}")

    # Step 5: Wiki-Graph 拡張検索検証
    print("\n[Step 5] Executing 1-Hop Graph-Augmented Search Verification...")
    search_engine = WikiGraphSearchEngine(indexer=indexer)
    search_res = search_engine.search(
        query="Explain embedding models and LLM evaluation benchmarks",
        wiki_dir=wiki_base,
        top_k=2,
    )

    print("\n--- 【検索 ＆ LLM 統合要約回答】 ---")
    print(f"Query: '{search_res.query}'")
    print(f"Hits: {len(search_res.main_hits)} main notes, {len(search_res.traversed_glossary_terms)} glossary terms")
    print(f"\n[Integrated LLM Answer Preview]:\n{search_res.integrated_answer[:350]}...")

    print("\n==========================================================================")
    print(f"🏆 AUDIT COMPLETE: {'ALL CHECKS PASSED PERFECTLY 🎉' if report.is_healthy and indexed_cnt > 0 else 'AUDIT FAILED'}")
    print("==========================================================================")


if __name__ == "__main__":
    run_ollama_qwen_embedding_audit()

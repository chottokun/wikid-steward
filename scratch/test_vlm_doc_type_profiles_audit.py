from pathlib import Path
import shutil

from wikid_steward.core.config import load_app_config
from wikid_steward.core.profiles import (
    DRAWING_PROFILE,
    DRAWING_SBOM_PROFILE,
    PAPER_PROFILE,
    resolve_profile,
)


def run_vlm_doc_type_profiles_audit():
    print("==========================================================================")
    print("      📐 THOROUGH DOC_TYPE VLM PROFILE & SUB-CONFIG AUDIT")
    print("==========================================================================")

    base_dir = Path.cwd()
    test_root = base_dir / "test_output" / "doc_type_vlm_audit"
    if test_root.exists():
        shutil.rmtree(test_root)

    test_root.mkdir(parents=True, exist_ok=True)
    raw_dir = test_root / "_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 1. 論文 (paper) のディレクトリポリシー検証
    paper_file = raw_dir / "paper" / "survey.pdf"
    paper_file.parent.mkdir(parents=True, exist_ok=True)
    paper_file.touch()

    prof_paper, src_paper, _ = resolve_profile(paper_file, raw_dir)
    print(f"\n[Test 1] Academic Paper Profile Resolution ({paper_file.relative_to(raw_dir)}):")
    print(f"  -> Profile Name: {prof_paper.name}")
    print(f"  -> Scale: {prof_paper.images_scale} (Expected: 2.0)")
    print(f"  -> OCR: {prof_paper.do_ocr}")
    print(f"  -> Format: {prof_paper.extraction_format}")
    print(f"  -> VLM Prompt Preview: {prof_paper.vlm_prompt[:60]}...")

    assert prof_paper.name == "paper"
    assert prof_paper.images_scale == 2.0
    assert "X軸・Y軸" in prof_paper.vlm_prompt

    # 2. 技術図面 (drawing) のディレクトリポリシー検証
    drawing_file = raw_dir / "drawing" / "component_cad.pdf"
    drawing_file.parent.mkdir(parents=True, exist_ok=True)
    drawing_file.touch()

    prof_draw, src_draw, _ = resolve_profile(drawing_file, raw_dir)
    print(f"\n[Test 2] Technical Drawing Profile Resolution ({drawing_file.relative_to(raw_dir)}):")
    print(f"  -> Profile Name: {prof_draw.name}")
    print(f"  -> Scale: {prof_draw.images_scale} (Expected: 3.0)")
    print(f"  -> OCR: {prof_draw.do_ocr} (Expected: True)")
    print(f"  -> Format: {prof_draw.extraction_format}")
    print(f"  -> VLM Prompt Preview: {prof_draw.vlm_prompt[:60]}...")

    assert prof_draw.name == "drawing"
    assert prof_draw.images_scale == 3.0
    assert prof_draw.do_ocr is True
    assert "寸法値" in prof_draw.vlm_prompt and "公差表記" in prof_draw.vlm_prompt

    # 3. 図面 SBOM (drawing_sbom) のディレクトリポリシー検証
    sbom_file = raw_dir / "sbom" / "parts_list.pdf"
    sbom_file.parent.mkdir(parents=True, exist_ok=True)
    sbom_file.touch()

    prof_sbom, src_sbom, _ = resolve_profile(sbom_file, raw_dir)
    print(f"\n[Test 3] Drawing SBOM Profile Resolution ({sbom_file.relative_to(raw_dir)}):")
    print(f"  -> Profile Name: {prof_sbom.name}")
    print(f"  -> Scale: {prof_sbom.images_scale} (Expected: 2.5)")
    print(f"  -> OCR: {prof_sbom.do_ocr} (Expected: True)")
    print(f"  -> Format: {prof_sbom.extraction_format} (Expected: html_table)")
    print(f"  -> VLM Prompt Preview: {prof_sbom.vlm_prompt[:60]}...")

    assert prof_sbom.name == "drawing_sbom"
    assert prof_sbom.extraction_format == "html_table"
    assert "部品構成表" in prof_sbom.vlm_prompt

    # 4. サブディレクトリ (profiles/custom_spec.yaml) の動的サブコンフィグ読込テスト
    (test_root / "config.yaml").write_text("paths:\n  raw_dir: _raw\n", encoding="utf-8")
    profiles_dir = test_root / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    custom_yaml = profiles_dir / "custom_spec.yaml"
    custom_yaml.write_text(
        """
doc_type: "Custom Spec"
do_ocr: true
images_scale: 4.0
vlm_prompt: "カスタムスペック専用プロンプト"
extraction_format: "structured_json"
""",
        encoding="utf-8",
    )

    app_cfg = load_app_config(base_dir=test_root)
    print(f"\n[Test 4] Sub-Config Directory Dynamic Loading ({custom_yaml.name}):")
    print(f"  -> Loaded Profiles Keys: {list(app_cfg.profiles.keys())}")
    custom_p = app_cfg.profiles.get("custom_spec")

    assert custom_p is not None, "FAILED: custom_spec.yaml was not loaded from profiles/ directory!"
    assert custom_p.doc_type == "Custom Spec"
    assert custom_p.images_scale == 4.0
    assert custom_p.vlm_prompt == "カスタムスペック専用プロンプト"
    print("  -> Sub-config Result: 100% PASSED 🎉 (profiles/custom_spec.yaml dynamically loaded)")

    print("\n==========================================================================")
    print("🏆 ALL DOC_TYPE VLM PROFILE & SUB-CONFIG TESTS PASSED PERFECTLY!")
    print("==========================================================================")


if __name__ == "__main__":
    run_vlm_doc_type_profiles_audit()

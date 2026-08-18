from pathlib import Path

from wikid_steward.core.profiles import (
    resolve_profile,
)


def test_resolve_profile_sidecar_yaml(tmp_path: Path):
    base_raw = tmp_path / "_raw"
    pdf_file = base_raw / "proj" / "doc.pdf"
    sidecar_yaml = base_raw / "proj" / "doc.yaml"

    pdf_file.parent.mkdir(parents=True)
    pdf_file.write_text("fake pdf")
    sidecar_yaml.write_text(
        "profile: drawing\nimages_scale: 3.5\ncustom_metadata:\n  rev: A",
        encoding="utf-8",
    )

    profile, source, custom_meta = resolve_profile(pdf_file, base_raw)
    assert profile.name == "drawing"
    assert source == "sidecar_yaml"
    assert profile.images_scale == 3.5
    assert custom_meta.get("rev") == "A"


def test_resolve_profile_directory_policy_drawing(tmp_path: Path):
    base_raw = tmp_path / "_raw"
    pdf_file = base_raw / "drawings" / "component_dwg.pdf"
    pdf_file.parent.mkdir(parents=True)
    pdf_file.write_text("fake pdf")

    profile, source, custom_meta = resolve_profile(pdf_file, base_raw)
    assert profile.name == "drawing"
    assert source == "directory_policy"


def test_resolve_profile_directory_policy_japanese_drawing(tmp_path: Path):
    base_raw = tmp_path / "_raw"
    pdf_file = base_raw / "設計図面" / "dwg_01.pdf"
    pdf_file.parent.mkdir(parents=True)
    pdf_file.write_text("fake pdf")

    profile, source, custom_meta = resolve_profile(pdf_file, base_raw)
    assert profile.name == "drawing"
    assert source == "directory_policy"


def test_resolve_profile_default_fallback(tmp_path: Path):
    base_raw = tmp_path / "_raw"
    pdf_file = base_raw / "general" / "unknown_doc.pdf"
    pdf_file.parent.mkdir(parents=True)
    pdf_file.write_text("fake pdf")

    profile, source, custom_meta = resolve_profile(pdf_file, base_raw)
    assert profile.name == "paper"
    assert source == "default"

from pathlib import Path

from wikid_steward.core.types_schema import OKFTypeRegistry


def test_get_type_case_insensitivity(tmp_path: Path) -> None:
    registry = OKFTypeRegistry(base_dir=tmp_path)

    # Concept exists by default in DEFAULT_OKF_TYPES
    type_def = registry.get_type("Concept")
    assert type_def is not None
    assert type_def.name == "Concept"

    # Lowercase
    type_def_lower = registry.get_type("concept")
    assert type_def_lower == type_def

    # Uppercase
    type_def_upper = registry.get_type("CONCEPT")
    assert type_def_upper == type_def

    # Mixed case
    type_def_mixed = registry.get_type("cOnCePt")
    assert type_def_mixed == type_def


def test_get_type_multi_word_name(tmp_path: Path) -> None:
    registry = OKFTypeRegistry(base_dir=tmp_path)

    type_def = registry.get_type("Architecture Decision")
    assert type_def is not None
    assert type_def.name == "Architecture Decision"

    type_def_lower = registry.get_type("architecture decision")
    assert type_def_lower == type_def


def test_get_type_non_existent(tmp_path: Path) -> None:
    registry = OKFTypeRegistry(base_dir=tmp_path)

    assert registry.get_type("NonExistentType") is None
    assert registry.get_type("unknown") is None


def test_get_type_edge_cases(tmp_path: Path) -> None:
    registry = OKFTypeRegistry(base_dir=tmp_path)

    # Empty string
    assert registry.get_type("") is None

    # Whitespace inputs (without trimming, " concept" won't match "concept")
    assert registry.get_type(" concept") is None
    assert registry.get_type("concept ") is None
    assert registry.get_type("   ") is None

    # Special characters
    assert registry.get_type("!@#$%^&*()") is None

    # Unicode characters
    assert registry.get_type("概念") is None


def test_get_type_custom_yaml(tmp_path: Path) -> None:
    custom_yaml = tmp_path / "types.yaml"
    custom_yaml.write_text(
        """
types:
  - name: "Custom Component"
    description: "Custom component type"
    required_sections:
      - "## Overview"
    tags:
      - "custom"
    routing_dir: "wiki/custom"
""",
        encoding="utf-8",
    )

    registry = OKFTypeRegistry(base_dir=tmp_path)

    type_def = registry.get_type("Custom Component")
    assert type_def is not None
    assert type_def.name == "Custom Component"
    assert type_def.routing_dir == "wiki/custom"

    # Case insensitive match for custom type
    assert registry.get_type("custom component") == type_def
    assert registry.get_type("CUSTOM COMPONENT") == type_def


def test_list_types(tmp_path: Path) -> None:
    registry = OKFTypeRegistry(base_dir=tmp_path)
    all_types = registry.list_types()
    assert isinstance(all_types, list)
    assert len(all_types) >= 6  # DEFAULT_OKF_TYPES count

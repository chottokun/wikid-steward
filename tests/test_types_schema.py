from pathlib import Path

import pytest

from wikid_steward.core.types_schema import DEFAULT_OKF_TYPES, OKFTypeRegistry


def test_okf_type_registry_defaults(tmp_path: Path):
    registry = OKFTypeRegistry(base_dir=tmp_path)
    types_list = registry.list_types()

    assert len(types_list) == len(DEFAULT_OKF_TYPES)
    concept_type = registry.get_type("Concept")
    assert concept_type is not None
    assert concept_type.name == "Concept"
    assert concept_type.routing_dir == "wiki/concepts"

    # Test case insensitive lookup
    assert registry.get_type("concept") == concept_type
    assert registry.get_type("nonexistent") is None


def test_okf_type_registry_valid_yaml(tmp_path: Path):
    types_yaml = tmp_path / "types.yaml"
    types_yaml.write_text(
        """
types:
  - name: CustomType
    description: A custom type definition
    required_sections:
      - "## Section 1"
    tags:
      - custom
    routing_dir: wiki/custom
""",
        encoding="utf-8",
    )

    registry = OKFTypeRegistry(base_dir=tmp_path)
    custom_type = registry.get_type("customtype")
    assert custom_type is not None
    assert custom_type.name == "CustomType"
    assert custom_type.description == "A custom type definition"
    assert custom_type.required_sections == ["## Section 1"]
    assert custom_type.tags == ["custom"]
    assert custom_type.routing_dir == "wiki/custom"


def test_okf_type_registry_profiles_location(tmp_path: Path):
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    types_yaml = profiles_dir / "types.yaml"
    types_yaml.write_text(
        """
types:
  - name: ProfileType
    description: Type defined in profiles/types.yaml
""",
        encoding="utf-8",
    )

    registry = OKFTypeRegistry(base_dir=tmp_path)
    profile_type = registry.get_type("ProfileType")
    assert profile_type is not None
    assert profile_type.name == "ProfileType"


def test_okf_type_registry_malformed_yaml(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    types_yaml = tmp_path / "types.yaml"
    # Write invalid YAML content that raises a ScannerError or ParserError
    types_yaml.write_text("types: [invalid yaml : : :", encoding="utf-8")

    registry = OKFTypeRegistry(base_dir=tmp_path)

    # Check that default types are preserved
    assert registry.get_type("Concept") is not None

    # Check that error warning was logged/printed
    captured = capsys.readouterr()
    assert "Warning: Failed to load types schema from" in captured.out
    assert str(types_yaml) in captured.out

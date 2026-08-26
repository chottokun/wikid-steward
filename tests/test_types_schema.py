from pathlib import Path

from wikid_steward.core.types_schema import DEFAULT_OKF_TYPES, OKFTypeRegistry


def test_okf_type_registry_init_empty_dir(tmp_path: Path):
    """Test initializing OKFTypeRegistry with an empty directory loads DEFAULT_OKF_TYPES."""
    registry = OKFTypeRegistry(base_dir=tmp_path)
    assert len(registry.list_types()) == len(DEFAULT_OKF_TYPES)
    for default_type in DEFAULT_OKF_TYPES:
        fetched = registry.get_type(default_type.name)
        assert fetched is not None
        assert fetched.name == default_type.name


def test_okf_type_registry_init_str_path(tmp_path: Path):
    """Test initializing OKFTypeRegistry with base_dir as a string path."""
    registry = OKFTypeRegistry(base_dir=str(tmp_path))
    assert registry.base_dir == tmp_path
    assert len(registry.list_types()) == len(DEFAULT_OKF_TYPES)


def test_okf_type_registry_init_none(monkeypatch, tmp_path: Path):
    """Test initializing OKFTypeRegistry with None uses Path.cwd()."""
    monkeypatch.chdir(tmp_path)
    registry = OKFTypeRegistry(base_dir=None)
    assert registry.base_dir == tmp_path
    assert len(registry.list_types()) == len(DEFAULT_OKF_TYPES)


def test_okf_type_registry_custom_types_yaml(tmp_path: Path):
    """Test loading custom OKF type definition from types.yaml in base_dir."""
    yaml_content = """
types:
  - name: CustomType
    description: Custom description
    required_sections:
      - "## Custom Section"
    tags:
      - custom
    routing_dir: wiki/custom
"""
    (tmp_path / "types.yaml").write_text(yaml_content, encoding="utf-8")
    registry = OKFTypeRegistry(base_dir=tmp_path)

    custom = registry.get_type("CustomType")
    assert custom is not None
    assert custom.name == "CustomType"
    assert custom.description == "Custom description"
    assert custom.required_sections == ["## Custom Section"]
    assert custom.tags == ["custom"]
    assert custom.routing_dir == "wiki/custom"


def test_okf_type_registry_custom_types_yml(tmp_path: Path):
    """Test loading custom OKF type definition from types.yml in base_dir."""
    yaml_content = """
types:
  - name: YmlType
    description: Yml description
"""
    (tmp_path / "types.yml").write_text(yaml_content, encoding="utf-8")
    registry = OKFTypeRegistry(base_dir=tmp_path)

    custom = registry.get_type("ymltype")
    assert custom is not None
    assert custom.name == "YmlType"
    assert custom.description == "Yml description"


def test_okf_type_registry_custom_profiles_types_yaml(tmp_path: Path):
    """Test loading custom OKF type definition from profiles/types.yaml in base_dir."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    yaml_content = """
types:
  - name: ProfileType
    description: Profile description
"""
    (profiles_dir / "types.yaml").write_text(yaml_content, encoding="utf-8")
    registry = OKFTypeRegistry(base_dir=tmp_path)

    custom = registry.get_type("PROFILETYPE")
    assert custom is not None
    assert custom.name == "ProfileType"


def test_okf_type_registry_get_type_unknown(tmp_path: Path):
    """Test get_type returns None for nonexistent type."""
    registry = OKFTypeRegistry(base_dir=tmp_path)
    assert registry.get_type("NonExistent") is None


def test_okf_type_registry_malformed_yaml(tmp_path: Path, capsys):
    """Test error handling when loading malformed types.yaml."""
    (tmp_path / "types.yaml").write_text("invalid: [yaml: content", encoding="utf-8")
    registry = OKFTypeRegistry(base_dir=tmp_path)
    captured = capsys.readouterr()

    assert "Warning: Failed to load types schema" in captured.out
    # Should still contain DEFAULT_OKF_TYPES
    assert len(registry.list_types()) == len(DEFAULT_OKF_TYPES)

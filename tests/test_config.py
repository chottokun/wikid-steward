import os
from pathlib import Path
from wikid_steward.core.config import load_app_config, get_config


def test_load_app_config_from_yaml(tmp_path: Path):
    yaml_content = """
llm:
  provider: "openai"
  base_url: "https://api.openai.com/v1"
  model: "gpt-4o"
vlm:
  enabled: false
  model: "vlm-custom"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")

    cfg = load_app_config(config_path=config_file, base_dir=tmp_path)

    assert cfg.llm.provider == "openai"
    assert cfg.llm.base_url == "https://api.openai.com/v1"
    assert cfg.llm.model == "gpt-4o"
    assert cfg.vlm.enabled is False
    assert cfg.vlm.model == "vlm-custom"


def test_env_override_priority(tmp_path: Path):
    yaml_content = """
llm:
  model: "yaml-model"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")

    # 環境変数で上書き
    os.environ["OPENAI_MODEL"] = "env-override-model"
    try:
        cfg = load_app_config(config_path=config_file, base_dir=tmp_path)
        # 環境変数 (env-override-model) が config.yaml より優先されること
        assert cfg.llm.model == "env-override-model"
    finally:
        os.environ.pop("OPENAI_MODEL", None)

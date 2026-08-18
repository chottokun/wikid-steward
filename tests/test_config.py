import os
from pathlib import Path

from wikid_steward.core.config import load_app_config


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
        assert cfg.llm.model == "env-override-model"
    finally:
        if "OPENAI_MODEL" in os.environ:
            del os.environ["OPENAI_MODEL"]


def test_env_override_all_new_settings(tmp_path: Path):
    yaml_content = """
llm:
  provider: "ollama"
vlm:
  enabled: true
paths:
  wiki_dir: "wiki"
vector_db:
  url: "http://localhost:6333"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")

    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["LLM_BASE_URL"] = "http://custom-llm:8000/v1"
    os.environ["LLM_API_KEY"] = "sk-secretllm"
    os.environ["LLM_MODEL"] = "custom-llm-model"
    os.environ["LLM_TEMPERATURE"] = "0.7"
    os.environ["LLM_MAX_TOKENS"] = "1024"

    os.environ["VLM_ENABLED"] = "false"
    os.environ["VLM_PROVIDER"] = "custom-vlm"
    os.environ["VLM_MODEL"] = "custom-vlm-model"
    os.environ["VLM_ENDPOINT"] = "http://vlm-server:1234"
    os.environ["VLM_API_KEY"] = "sk-secretvlm"
    os.environ["VLM_PROMPT"] = "custom prompt"

    os.environ["RAW_DIR"] = "custom_raw"
    os.environ["RAW_SOURCES_DIR"] = "custom_raw_sources"
    os.environ["STAGING_DIR"] = "custom_staging"
    os.environ["WIKI_DIR"] = "custom_wiki"

    os.environ["RELINKER_STOP_WORDS"] = "AAA,BBB,CCC"
    os.environ["RELINKER_MIN_TERM_LENGTH"] = "5"

    os.environ["VECTOR_DB_PROVIDER"] = "custom-db"
    os.environ["QDRANT_URL"] = "http://qdrant-server:8500"
    os.environ["QDRANT_API_KEY"] = "qdrant-secret"
    os.environ["VECTOR_DB_COLLECTION_NAME"] = "custom_collection"
    os.environ["VECTOR_DB_MAX_CONTEXT_TOKENS"] = "9999"
    os.environ["VECTOR_DB_EMBEDDING_PROVIDER"] = "custom-embedding"
    os.environ["VECTOR_DB_EMBEDDING_BASE_URL"] = "http://emb:7000/v1"
    os.environ["VECTOR_DB_EMBEDDING_MODEL"] = "custom-emb-model"
    os.environ["VECTOR_DB_EMBEDDING_API_KEY"] = "sk-secretemb"
    os.environ["VECTOR_DB_MAX_HUB_DEGREE"] = "100"
    os.environ["VECTOR_DB_MAX_TRAVERSAL_TOKENS"] = "3000"

    try:
        cfg = load_app_config(config_path=config_file, base_dir=tmp_path)

        # Asserts LLM
        assert cfg.llm.provider == "openai"
        assert cfg.llm.base_url == "http://custom-llm:8000/v1"
        assert cfg.llm.api_key == "sk-secretllm"
        assert cfg.llm.model == "custom-llm-model"
        assert cfg.llm.temperature == 0.7
        assert cfg.llm.max_tokens == 1024

        # Asserts VLM
        assert cfg.vlm.enabled is False
        assert cfg.vlm.provider == "custom-vlm"
        assert cfg.vlm.model == "custom-vlm-model"
        assert cfg.vlm.endpoint == "http://vlm-server:1234"
        assert cfg.vlm.api_key == "sk-secretvlm"
        assert cfg.vlm.prompt == "custom prompt"

        # Asserts Paths
        assert cfg.paths.raw_dir == "custom_raw"
        assert cfg.paths.raw_sources_dir == "custom_raw_sources"
        assert cfg.paths.staging_dir == "custom_staging"
        assert cfg.paths.wiki_dir == "custom_wiki"

        # Asserts Relinker
        assert cfg.relinker.stop_words == ["AAA", "BBB", "CCC"]
        assert cfg.relinker.min_term_length == 5

        # Asserts Vector DB
        assert cfg.vector_db.provider == "custom-db"
        assert cfg.vector_db.url == "http://qdrant-server:8500"
        assert cfg.vector_db.api_key == "qdrant-secret"
        assert cfg.vector_db.collection_name == "custom_collection"
        assert cfg.vector_db.max_context_tokens == 9999
        assert cfg.vector_db.embedding_provider == "custom-embedding"
        assert cfg.vector_db.embedding_base_url == "http://emb:7000/v1"
        assert cfg.vector_db.embedding_model == "custom-emb-model"
        assert cfg.vector_db.embedding_api_key == "sk-secretemb"
        assert cfg.vector_db.max_hub_degree == 100
        assert cfg.vector_db.max_traversal_tokens == 3000

    finally:
        # Cleanup env vars
        keys = [
            "LLM_PROVIDER",
            "LLM_BASE_URL",
            "LLM_API_KEY",
            "LLM_MODEL",
            "LLM_TEMPERATURE",
            "LLM_MAX_TOKENS",
            "VLM_ENABLED",
            "VLM_PROVIDER",
            "VLM_MODEL",
            "VLM_ENDPOINT",
            "VLM_API_KEY",
            "VLM_PROMPT",
            "RAW_DIR",
            "RAW_SOURCES_DIR",
            "STAGING_DIR",
            "WIKI_DIR",
            "RELINKER_STOP_WORDS",
            "RELINKER_MIN_TERM_LENGTH",
            "VECTOR_DB_PROVIDER",
            "QDRANT_URL",
            "QDRANT_API_KEY",
            "VECTOR_DB_COLLECTION_NAME",
            "VECTOR_DB_MAX_CONTEXT_TOKENS",
            "VECTOR_DB_EMBEDDING_PROVIDER",
            "VECTOR_DB_EMBEDDING_BASE_URL",
            "VECTOR_DB_EMBEDDING_MODEL",
            "VECTOR_DB_EMBEDDING_API_KEY",
            "VECTOR_DB_MAX_HUB_DEGREE",
            "VECTOR_DB_MAX_TRAVERSAL_TOKENS",
        ]
        for key in keys:
            if key in os.environ:
                del os.environ[key]


def test_load_app_config_from_json(tmp_path: Path):
    json_content = """{
      "vector_db": {
        "max_hub_degree": 50,
        "max_traversal_tokens": 2000
      }
    }"""
    config_file = tmp_path / "config.json"
    config_file.write_text(json_content, encoding="utf-8")

    cfg = load_app_config(config_path=config_file, base_dir=tmp_path)

    assert cfg.vector_db.max_hub_degree == 50
    assert cfg.vector_db.max_traversal_tokens == 2000

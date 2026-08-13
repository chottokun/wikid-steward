import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml
from dotenv import load_dotenv

load_dotenv(override=False)


@dataclass
class LLMSettings:
    provider: str = "ollama"
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "ollama"
    model: str = "gemma4:latest"
    temperature: float = 0.2
    max_tokens: int = 2048


@dataclass
class VLMSettings:
    enabled: bool = True
    provider: str = "ollama"
    model: str = "qwen3.5:4b"
    endpoint: str = "http://localhost:11434"
    prompt: str = "この画像の概要を1〜2文程度で簡潔に日本語で説明してください。"


@dataclass
class PathSettings:
    raw_dir: str = "_raw"
    raw_sources_dir: str = "raw_sources"
    staging_dir: str = "staging"
    wiki_dir: str = "wiki"


@dataclass
class ProfileSetting:
    doc_type: str
    do_ocr: bool = False
    images_scale: float = 2.0
    table_mode: str = "accurate"


@dataclass
class RelinkerSettings:
    stop_words: list[str] = field(
        default_factory=lambda: [
            "AI",
            "NLP",
            "LLM",
            "LLMS",
            "DATA",
            "OUTPUT",
            "FILE",
            "PDF",
            "PAPER",
            "MODEL",
            "SYSTEM",
        ]
    )
    min_term_length: int = 3


@dataclass
class VectorDBSettings:
    provider: str = "qdrant"
    url: str = "http://localhost:6333"
    collection_name: str = "wikid_steward_knowledge"
    max_context_tokens: int = 4000
    embedding_provider: str = "ollama"  # "ollama", "openai", "fastembed"
    embedding_base_url: str = "http://localhost:11434/v1"
    embedding_model: str = "qwen3-embedding:0.6b"


@dataclass
class AppConfig:
    llm: LLMSettings = field(default_factory=LLMSettings)
    vlm: VLMSettings = field(default_factory=VLMSettings)
    paths: PathSettings = field(default_factory=PathSettings)
    profiles: dict[str, ProfileSetting] = field(
        default_factory=lambda: {
            "paper": ProfileSetting(doc_type="Academic Paper", do_ocr=False, images_scale=2.0),
            "drawing": ProfileSetting(doc_type="Technical Drawing", do_ocr=True, images_scale=3.0),
            "spreadsheet": ProfileSetting(doc_type="Data Sheet", do_ocr=False, images_scale=2.0),
            "presentation": ProfileSetting(doc_type="Presentation", do_ocr=False, images_scale=2.0),
        }
    )
    relinker: RelinkerSettings = field(default_factory=RelinkerSettings)
    vector_db: VectorDBSettings = field(default_factory=VectorDBSettings)
    config_file_path: Path | None = None


def load_app_config(
    config_path: Path | str | None = None, base_dir: Path | str | None = None
) -> AppConfig:
    """ハイブリッドカスケード方式 (環境変数/.env > config.yaml > デフォルト値) で全設定をロードする"""
    base = Path(base_dir) if base_dir else Path.cwd()
    cfg = AppConfig()

    target_config = None
    if config_path:
        target_config = Path(config_path)
    else:
        for possible in [base / "config.yaml", base / "config.yml", base / "config.json"]:
            if possible.exists():
                target_config = possible
                break

    if target_config and target_config.exists():
        try:
            raw_text = target_config.read_text(encoding="utf-8")
            data = yaml.safe_load(raw_text) or {}
            cfg.config_file_path = target_config

            # 1. LLM 設定
            if "llm" in data and isinstance(data["llm"], dict):
                d = data["llm"]
                cfg.llm.provider = d.get("provider", cfg.llm.provider)
                cfg.llm.base_url = d.get("base_url", cfg.llm.base_url)
                cfg.llm.api_key = d.get("api_key", cfg.llm.api_key)
                cfg.llm.model = d.get("model", cfg.llm.model)
                cfg.llm.temperature = float(d.get("temperature", cfg.llm.temperature))
                cfg.llm.max_tokens = int(d.get("max_tokens", cfg.llm.max_tokens))

            # 2. VLM 設定
            if "vlm" in data and isinstance(data["vlm"], dict):
                d = data["vlm"]
                cfg.vlm.enabled = bool(d.get("enabled", cfg.vlm.enabled))
                cfg.vlm.provider = d.get("provider", cfg.vlm.provider)
                cfg.vlm.model = d.get("model", cfg.vlm.model)
                cfg.vlm.endpoint = d.get("endpoint", cfg.vlm.endpoint)
                cfg.vlm.prompt = d.get("prompt", cfg.vlm.prompt)

            # 3. Paths 設定
            if "paths" in data and isinstance(data["paths"], dict):
                d = data["paths"]
                cfg.paths.raw_dir = d.get("raw_dir", cfg.paths.raw_dir)
                cfg.paths.raw_sources_dir = d.get("raw_sources_dir", cfg.paths.raw_sources_dir)
                cfg.paths.staging_dir = d.get("staging_dir", cfg.paths.staging_dir)
                cfg.paths.wiki_dir = d.get("wiki_dir", cfg.paths.wiki_dir)

            # 4. Profiles 設定
            if "profiles" in data and isinstance(data["profiles"], dict):
                prof_dict = {}
                for name, pdata in data["profiles"].items():
                    if isinstance(pdata, dict):
                        prof_dict[name] = ProfileSetting(
                            doc_type=pdata.get("doc_type", "General Document"),
                            do_ocr=bool(pdata.get("do_ocr", False)),
                            images_scale=float(pdata.get("images_scale", 2.0)),
                            table_mode=pdata.get("table_mode", "accurate"),
                        )
                if prof_dict:
                    cfg.profiles = prof_dict

            # 5. Relinker 設定
            if "relinker" in data and isinstance(data["relinker"], dict):
                d = data["relinker"]
                if "stop_words" in d and isinstance(d["stop_words"], list):
                    cfg.relinker.stop_words = d["stop_words"]
                cfg.relinker.min_term_length = int(d.get("min_term_length", cfg.relinker.min_term_length))

            # 6. Vector DB 設定
            if "vector_db" in data and isinstance(data["vector_db"], dict):
                d = data["vector_db"]
                cfg.vector_db.provider = d.get("provider", cfg.vector_db.provider)
                cfg.vector_db.url = d.get("url", cfg.vector_db.url)
                cfg.vector_db.collection_name = d.get("collection_name", cfg.vector_db.collection_name)
                cfg.vector_db.max_context_tokens = int(d.get("max_context_tokens", cfg.vector_db.max_context_tokens))
                cfg.vector_db.embedding_provider = d.get("embedding_provider", cfg.vector_db.embedding_provider)
                cfg.vector_db.embedding_base_url = d.get("embedding_base_url", cfg.vector_db.embedding_base_url)
                cfg.vector_db.embedding_model = d.get("embedding_model", cfg.vector_db.embedding_model)

        except Exception as e:
            print(f"Warning: Failed to load config file {target_config}: {e}")

    # 環境変数による最高優先度上書き
    if os.getenv("OPENAI_BASE_URL"):
        cfg.llm.base_url = os.environ["OPENAI_BASE_URL"]
    if os.getenv("OPENAI_API_KEY"):
        cfg.llm.api_key = os.environ["OPENAI_API_KEY"]
    if os.getenv("OPENAI_MODEL"):
        cfg.llm.model = os.environ["OPENAI_MODEL"]

    return cfg


_GLOBAL_CONFIG: AppConfig | None = None


def get_config(force_reload: bool = False) -> AppConfig:
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None or force_reload:
        _GLOBAL_CONFIG = load_app_config()
    return _GLOBAL_CONFIG

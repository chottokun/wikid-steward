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
    target_language: str = "Japanese"


@dataclass
class VLMSettings:
    enabled: bool = True
    provider: str = "ollama"
    model: str = "qwen3.5:4b"
    endpoint: str = "http://localhost:11434"
    api_key: str = ""
    prompt: str = "この画像の概要を1〜2文程度で簡潔に日本語で説明してください。"


@dataclass
class PathSettings:
    raw_dir: str = "_raw"
    raw_sources_dir: str = "raw_sources"
    staging_dir: str = "staging"
    wiki_dir: str = "wiki"
    stubs_dir: str = "wiki/stubs"


@dataclass
class ProfileSetting:
    doc_type: str = "General Document"
    do_ocr: bool = False
    images_scale: float = 2.0
    table_mode: str = "accurate"
    vlm_prompt: str | None = None
    extraction_format: str = "markdown"


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
    mode: str = "first_hit_per_section"  # "first_hit_per_section" | "all"


@dataclass
class RetroCompilationSettings:
    min_backlinks: int = 3


@dataclass
class VectorDBSettings:
    provider: str = "qdrant"
    url: str = "http://localhost:6333"
    api_key: str = ""
    collection_name: str = "wikid_steward_knowledge"
    max_context_tokens: int = 4000
    embedding_provider: str = "ollama"  # "ollama", "openai", "fastembed"
    embedding_base_url: str = "http://localhost:11434/v1"
    embedding_model: str = "qwen3-embedding:0.6b"
    embedding_api_key: str = ""
    max_hub_degree: int = 25  # 巨大ハブノード度数閾値
    max_traversal_tokens: int = 1200  # 1-Hop 巡回読み込みトークン上限


@dataclass
class CompilerSettings:
    auto_moc: bool = True  # コンパイル完了時に MOC (index.md) を自動更新
    extract_full_text: bool = False  # 用語・概念抽出時に全文コンテキストを使用 (長大モデル使用時は true)
    max_extract_chars: int = 12000  # 用語抽出時の最大文字数上限 (0で無制限)
    default_status: str = "draft"  # デフォルトステータス (draft | stable)


@dataclass
class AppConfig:
    llm: LLMSettings = field(default_factory=LLMSettings)
    vlm: VLMSettings = field(default_factory=VLMSettings)
    paths: PathSettings = field(default_factory=PathSettings)
    compiler: CompilerSettings = field(default_factory=CompilerSettings)
    relinker: RelinkerSettings = field(default_factory=RelinkerSettings)
    retro_compilation: RetroCompilationSettings = field(
        default_factory=RetroCompilationSettings
    )
    vector_db: VectorDBSettings = field(default_factory=VectorDBSettings)
    profiles: dict[str, ProfileSetting] = field(
        default_factory=lambda: {
            "paper": ProfileSetting(
                doc_type="Academic Paper",
                do_ocr=False,
                images_scale=2.0,
                extraction_format="markdown",
            ),
            "drawing": ProfileSetting(
                doc_type="Technical Drawing",
                do_ocr=True,
                images_scale=3.0,
                extraction_format="markdown",
            ),
            "drawing_sbom": ProfileSetting(
                doc_type="Drawing SBOM",
                do_ocr=True,
                images_scale=2.5,
                extraction_format="html_table",
            ),
        }
    )
    relinker: RelinkerSettings = field(default_factory=RelinkerSettings)
    retro_compilation: RetroCompilationSettings = field(
        default_factory=RetroCompilationSettings
    )
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
        for possible in [base / "config.yaml", base / "config.yml"]:
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
                cfg.llm.target_language = d.get("target_language", cfg.llm.target_language)

            # 2. VLM 設定
            if "vlm" in data and isinstance(data["vlm"], dict):
                d = data["vlm"]
                cfg.vlm.enabled = bool(d.get("enabled", cfg.vlm.enabled))
                cfg.vlm.provider = d.get("provider", cfg.vlm.provider)
                cfg.vlm.model = d.get("model", cfg.vlm.model)
                cfg.vlm.endpoint = d.get("endpoint", cfg.vlm.endpoint)
                cfg.vlm.api_key = d.get("api_key", cfg.vlm.api_key)
                cfg.vlm.prompt = d.get("prompt", cfg.vlm.prompt)

            # 3. Paths 設定
            if "paths" in data and isinstance(data["paths"], dict):
                d = data["paths"]
                cfg.paths.raw_dir = d.get("raw_dir", cfg.paths.raw_dir)
                cfg.paths.raw_sources_dir = d.get("raw_sources_dir", cfg.paths.raw_sources_dir)
                cfg.paths.staging_dir = d.get("staging_dir", cfg.paths.staging_dir)
                cfg.paths.wiki_dir = d.get("wiki_dir", cfg.paths.wiki_dir)
                cfg.paths.stubs_dir = d.get("stubs_dir", cfg.paths.stubs_dir)

            # 4. Profiles 設定 (config.yaml 内 + profiles/ ディレクトリからのサブコンフィグ)
            if "profiles" in data and isinstance(data["profiles"], dict):
                prof_dict = {}
                for name, pdata in data["profiles"].items():
                    if isinstance(pdata, dict):
                        prof_dict[name] = ProfileSetting(
                            doc_type=pdata.get("doc_type", "General Document"),
                            do_ocr=bool(pdata.get("do_ocr", False)),
                            images_scale=float(pdata.get("images_scale", 2.0)),
                            table_mode=pdata.get("table_mode", "accurate"),
                            vlm_prompt=pdata.get("vlm_prompt", None),
                            extraction_format=pdata.get("extraction_format", "markdown"),
                        )
                if prof_dict:
                    cfg.profiles = prof_dict

            # profiles/ サブディレクトリが存在する場合の個別の doc_type config ロード
            profiles_dir = base / "profiles"
            if profiles_dir.exists() and profiles_dir.is_dir():
                for p_file in profiles_dir.glob("*.yaml"):
                    p_name = p_file.stem
                    try:
                        p_data = yaml.safe_load(p_file.read_text(encoding="utf-8")) or {}
                        cfg.profiles[p_name] = ProfileSetting(
                            doc_type=p_data.get("doc_type", "General Document"),
                            do_ocr=bool(p_data.get("do_ocr", False)),
                            images_scale=float(p_data.get("images_scale", 2.0)),
                            table_mode=p_data.get("table_mode", "accurate"),
                            vlm_prompt=p_data.get("vlm_prompt", None),
                            extraction_format=p_data.get("extraction_format", "markdown"),
                        )
                    except Exception as pe:
                        print(f"Warning: Failed to load profile sub-config {p_file}: {pe}")

            # 5. Relinker 設定
            if "relinker" in data and isinstance(data["relinker"], dict):
                d = data["relinker"]
                if "stop_words" in d and isinstance(d["stop_words"], list):
                    cfg.relinker.stop_words = d["stop_words"]
                cfg.relinker.min_term_length = int(d.get("min_term_length", cfg.relinker.min_term_length))
                cfg.relinker.mode = d.get("mode", cfg.relinker.mode)

            # 6. Retro Compilation 設定
            if "retro_compilation" in data and isinstance(data["retro_compilation"], dict):
                d = data["retro_compilation"]
                cfg.retro_compilation.min_backlinks = int(
                    d.get("min_backlinks", cfg.retro_compilation.min_backlinks)
                )

            # 7. Vector DB 設定
            if "vector_db" in data and isinstance(data["vector_db"], dict):
                d = data["vector_db"]
                cfg.vector_db.provider = d.get("provider", cfg.vector_db.provider)
                cfg.vector_db.url = d.get("url", cfg.vector_db.url)
                cfg.vector_db.api_key = d.get("api_key", cfg.vector_db.api_key)
                cfg.vector_db.collection_name = d.get("collection_name", cfg.vector_db.collection_name)
                cfg.vector_db.max_context_tokens = int(d.get("max_context_tokens", cfg.vector_db.max_context_tokens))
                cfg.vector_db.embedding_provider = d.get("embedding_provider", cfg.vector_db.embedding_provider)
                cfg.vector_db.embedding_base_url = d.get("embedding_base_url", cfg.vector_db.embedding_base_url)
                cfg.vector_db.embedding_model = d.get("embedding_model", cfg.vector_db.embedding_model)
                cfg.vector_db.embedding_api_key = d.get("embedding_api_key", cfg.vector_db.embedding_api_key)
                cfg.vector_db.max_hub_degree = int(d.get("max_hub_degree", cfg.vector_db.max_hub_degree))
                cfg.vector_db.max_traversal_tokens = int(d.get("max_traversal_tokens", cfg.vector_db.max_traversal_tokens))

            # 8. Compiler 設定
            if "compiler" in data and isinstance(data["compiler"], dict):
                d = data["compiler"]
                cfg.compiler.auto_moc = bool(d.get("auto_moc", cfg.compiler.auto_moc))
                cfg.compiler.extract_full_text = bool(d.get("extract_full_text", cfg.compiler.extract_full_text))
                cfg.compiler.max_extract_chars = int(d.get("max_extract_chars", cfg.compiler.max_extract_chars))
                cfg.compiler.default_status = str(d.get("default_status", cfg.compiler.default_status))

        except Exception as e:
            print(f"Warning: Failed to load config file {target_config}: {e}")

    # 環境変数による最高優先度上書き

    def parse_bool(val: str | None) -> bool:
        if not val:
            return False
        return val.strip().lower() in ("true", "1", "yes", "on")

    # 1. LLM
    if os.getenv("LLM_PROVIDER"):
        cfg.llm.provider = os.environ["LLM_PROVIDER"]
    if os.getenv("LLM_BASE_URL"):
        cfg.llm.base_url = os.environ["LLM_BASE_URL"]
    elif os.getenv("OPENAI_BASE_URL"):
        cfg.llm.base_url = os.environ["OPENAI_BASE_URL"]
    if os.getenv("LLM_API_KEY"):
        cfg.llm.api_key = os.environ["LLM_API_KEY"]
    elif os.getenv("OPENAI_API_KEY"):
        cfg.llm.api_key = os.environ["OPENAI_API_KEY"]
    if os.getenv("LLM_MODEL"):
        cfg.llm.model = os.environ["LLM_MODEL"]
    elif os.getenv("OPENAI_MODEL"):
        cfg.llm.model = os.environ["OPENAI_MODEL"]
    if os.getenv("LLM_TEMPERATURE"):
        cfg.llm.temperature = float(os.environ["LLM_TEMPERATURE"])
    if os.getenv("LLM_MAX_TOKENS"):
        cfg.llm.max_tokens = int(os.environ["LLM_MAX_TOKENS"])
    if os.getenv("LLM_TARGET_LANGUAGE"):
        cfg.llm.target_language = os.environ["LLM_TARGET_LANGUAGE"]

    # 2. VLM
    if os.getenv("VLM_ENABLED"):
        cfg.vlm.enabled = parse_bool(os.environ["VLM_ENABLED"])
    if os.getenv("VLM_PROVIDER"):
        cfg.vlm.provider = os.environ["VLM_PROVIDER"]
    if os.getenv("VLM_MODEL"):
        cfg.vlm.model = os.environ["VLM_MODEL"]
    if os.getenv("VLM_ENDPOINT"):
        cfg.vlm.endpoint = os.environ["VLM_ENDPOINT"]
    if os.getenv("VLM_API_KEY"):
        cfg.vlm.api_key = os.environ["VLM_API_KEY"]
    if os.getenv("VLM_PROMPT"):
        cfg.vlm.prompt = os.environ["VLM_PROMPT"]

    # 3. Paths
    if os.getenv("PATHS_RAW_DIR"):
        cfg.paths.raw_dir = os.environ["PATHS_RAW_DIR"]
    elif os.getenv("RAW_DIR"):
        cfg.paths.raw_dir = os.environ["RAW_DIR"]
    if os.getenv("PATHS_RAW_SOURCES_DIR"):
        cfg.paths.raw_sources_dir = os.environ["PATHS_RAW_SOURCES_DIR"]
    elif os.getenv("RAW_SOURCES_DIR"):
        cfg.paths.raw_sources_dir = os.environ["RAW_SOURCES_DIR"]
    if os.getenv("PATHS_STAGING_DIR"):
        cfg.paths.staging_dir = os.environ["PATHS_STAGING_DIR"]
    elif os.getenv("STAGING_DIR"):
        cfg.paths.staging_dir = os.environ["STAGING_DIR"]
    if os.getenv("PATHS_WIKI_DIR"):
        cfg.paths.wiki_dir = os.environ["PATHS_WIKI_DIR"]
    elif os.getenv("WIKI_DIR"):
        cfg.paths.wiki_dir = os.environ["WIKI_DIR"]
    if os.getenv("PATHS_STUBS_DIR"):
        cfg.paths.stubs_dir = os.environ["PATHS_STUBS_DIR"]
    elif os.getenv("STUBS_DIR"):
        cfg.paths.stubs_dir = os.environ["STUBS_DIR"]

    # 4. Relinker
    if os.getenv("RELINKER_STOP_WORDS"):
        cfg.relinker.stop_words = [w.strip() for w in os.environ["RELINKER_STOP_WORDS"].split(",")]
    if os.getenv("RELINKER_MIN_TERM_LENGTH"):
        cfg.relinker.min_term_length = int(os.environ["RELINKER_MIN_TERM_LENGTH"])

    # 5. Retro Compilation
    if os.getenv("RETRO_COMPILATION_MIN_BACKLINKS"):
        cfg.retro_compilation.min_backlinks = int(os.environ["RETRO_COMPILATION_MIN_BACKLINKS"])

    # 6. Vector DB
    if os.getenv("VECTOR_DB_PROVIDER"):
        cfg.vector_db.provider = os.environ["VECTOR_DB_PROVIDER"]
    if os.getenv("VECTOR_DB_URL"):
        cfg.vector_db.url = os.environ["VECTOR_DB_URL"]
    elif os.getenv("QDRANT_URL"):
        cfg.vector_db.url = os.environ["QDRANT_URL"]
    if os.getenv("VECTOR_DB_API_KEY"):
        cfg.vector_db.api_key = os.environ["VECTOR_DB_API_KEY"]
    elif os.getenv("QDRANT_API_KEY"):
        cfg.vector_db.api_key = os.environ["QDRANT_API_KEY"]
    if os.getenv("VECTOR_DB_COLLECTION_NAME"):
        cfg.vector_db.collection_name = os.environ["VECTOR_DB_COLLECTION_NAME"]
    if os.getenv("VECTOR_DB_MAX_CONTEXT_TOKENS"):
        cfg.vector_db.max_context_tokens = int(os.environ["VECTOR_DB_MAX_CONTEXT_TOKENS"])
    if os.getenv("VECTOR_DB_EMBEDDING_PROVIDER"):
        cfg.vector_db.embedding_provider = os.environ["VECTOR_DB_EMBEDDING_PROVIDER"]
    if os.getenv("VECTOR_DB_EMBEDDING_BASE_URL"):
        cfg.vector_db.embedding_base_url = os.environ["VECTOR_DB_EMBEDDING_BASE_URL"]
    if os.getenv("VECTOR_DB_EMBEDDING_MODEL"):
        cfg.vector_db.embedding_model = os.environ["VECTOR_DB_EMBEDDING_MODEL"]
    if os.getenv("VECTOR_DB_EMBEDDING_API_KEY"):
        cfg.vector_db.embedding_api_key = os.environ["VECTOR_DB_EMBEDDING_API_KEY"]
    if os.getenv("VECTOR_DB_MAX_HUB_DEGREE"):
        cfg.vector_db.max_hub_degree = int(os.environ["VECTOR_DB_MAX_HUB_DEGREE"])
    if os.getenv("VECTOR_DB_MAX_TRAVERSAL_TOKENS"):
        cfg.vector_db.max_traversal_tokens = int(os.environ["VECTOR_DB_MAX_TRAVERSAL_TOKENS"])

    return cfg


_GLOBAL_CONFIG: AppConfig | None = None


def get_config(force_reload: bool = False) -> AppConfig:
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None or force_reload:
        _GLOBAL_CONFIG = load_app_config()
    return _GLOBAL_CONFIG

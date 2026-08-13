from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml
from enum import Enum


class TableFormerMode(Enum):
    ACCURATE = "accurate"
    FAST = "fast"


@dataclass
class ParseProfile:
    """パース処理のポリシープロファイル"""

    name: str
    doc_type: str
    do_ocr: bool = False
    images_scale: float = 2.0
    table_mode: TableFormerMode = TableFormerMode.ACCURATE
    vlm_enabled: bool = False
    vlm_provider: str = "ollama"  # "ollama", "openai", "custom", "anthropic", "vllm" 等
    vlm_model: str = "qwen3.5:4b"
    vlm_endpoint: str = "http://localhost:11434"
    vlm_api_key: str = ""
    vlm_prompt: str = "この画像の概要を1〜2文程度で簡潔に日本語で説明してください。"
    extraction_format: str = "markdown"  # "markdown", "html_table", "structured_json"


# 1. 学術論文プロファイル (Academic Paper)
PAPER_PROFILE = ParseProfile(
    name="paper",
    doc_type="Academic Paper",
    do_ocr=False,
    images_scale=2.0,
    extraction_format="markdown",
    vlm_prompt=(
        "この論文中の図表（グラフ、構成図、概念図）の内容を日本語で解説してください：\n"
        "1. X軸・Y軸のラベル、単位、および比較条件\n"
        "2. 手法やモデル間の性能差、数値の増減傾向\n"
        "3. 図が示している核心的な結論やメッセージ"
    ),
)

# 2. 技術図面プロファイル (Technical Drawing) - 寸法・公差・照合番号特化
DRAWING_PROFILE = ParseProfile(
    name="drawing",
    doc_type="Technical Drawing",
    do_ocr=True,
    images_scale=3.0,  # 超高解像度 3.0x (文字潰れ防止)
    extraction_format="markdown",
    vlm_prompt=(
        "この技術図面・機構図から以下の重要情報を精度高く抽出・解釈してください：\n"
        "1. 図面内の主要寸法値および公差表記（例: 15.0±0.05mm, Φ12, Ra0.8等）\n"
        "2. 照合番号（バルーン番号・部品No）と幾何公差記号\n"
        "3. 注記（Material, Surface Finish, General Tolerances）"
    ),
)

# 3. 図面 SBOM / 部品構成表プロファイル (Drawing SBOM) - 表構造特化
DRAWING_SBOM_PROFILE = ParseProfile(
    name="drawing_sbom",
    doc_type="Drawing SBOM",
    do_ocr=True,
    images_scale=2.5,
    extraction_format="html_table",  # 構造化 HTML/Markdown 表を強制
    vlm_prompt=(
        "この部品構成表 (BOM / Parts List) を以下の標準表形式で正確に抽出してください：\n"
        "| Item (品番) | Part Number (図番) | Description (品名) | Qty (数量) | Material (材質) |"
    ),
)

SPREADSHEET_PROFILE = ParseProfile(
    name="spreadsheet",
    doc_type="Data Sheet",
    do_ocr=False,
    images_scale=2.0,
)

PRESENTATION_PROFILE = ParseProfile(
    name="presentation",
    doc_type="Presentation",
    do_ocr=False,
    images_scale=2.0,
)

PROFILES_MAP = {
    "paper": PAPER_PROFILE,
    "drawing": DRAWING_PROFILE,
    "drawing_sbom": DRAWING_SBOM_PROFILE,
    "spreadsheet": SPREADSHEET_PROFILE,
    "presentation": PRESENTATION_PROFILE,
}


def resolve_profile(
    raw_file_path: Path | str, base_raw_dir: Path | str
) -> tuple[ParseProfile, str, dict[str, Any]]:
    """原本ファイルパスと _raw ディレクトリから、パースプロファイル、判定元 (source)、カスタムメタデータを解決する。

    優先度規則:
    1. サイドカー YAML (file.yaml) の明示指定
    2. フォルダ名によるディレクトリポリシー判定
    3. 当てはまらない場合は完全デフォルト (PAPER_PROFILE)

    Args:
        raw_file_path: 対象原本ファイルのパス
        base_raw_dir: _raw ルートディレクトリのパス

    Returns:
        (ParseProfile, profile_source, custom_metadata_dict)
    """
    file_path = Path(raw_file_path)
    base_dir = Path(base_raw_dir)

    # 1. 優先度 1: サイドカー YAML のチェック (例: file.yaml または file.pdf.yaml)
    sidecar_candidates = [
        file_path.with_suffix(".yaml"),
        file_path.with_suffix(".yml"),
        Path(str(file_path) + ".yaml"),
    ]

    for sidecar in sidecar_candidates:
        if sidecar.exists():
            try:
                content = sidecar.read_text(encoding="utf-8")
                data = yaml.safe_load(content)
                if isinstance(data, dict):
                    prof_name = str(data.get("profile", "")).lower()
                    base_profile = PROFILES_MAP.get(prof_name, PAPER_PROFILE)

                    # プロパティ個別上書き
                    do_ocr = data.get("ocr", base_profile.do_ocr)
                    scale = float(
                        data.get("images_scale", base_profile.images_scale)
                    )
                    doc_type = data.get("doc_type", base_profile.doc_type)

                    resolved = ParseProfile(
                        name=base_profile.name,
                        doc_type=doc_type,
                        do_ocr=do_ocr,
                        images_scale=scale,
                    )
                    custom_meta = data.get("custom_metadata", {})
                    return resolved, "sidecar_yaml", custom_meta
            except Exception:
                pass

    # 2. 優先度 2: ディレクトリポリシーの判定 (フォルダ名キーワード)
    from wikid_steward.core.config import get_config
    app_cfg = get_config()

    try:
        rel_path = file_path.relative_to(base_dir)
        folder_parts = [p.lower() for p in rel_path.parts[:-1]]
        folder_str = "/".join(folder_parts)

        # 図面/SBOM フォルダキーワード
        if any(kw in folder_str for kw in ["sbom", "bom", "部品表"]):
            cfg_p = app_cfg.profiles.get("drawing_sbom")
            prof = DRAWING_SBOM_PROFILE
            if cfg_p:
                prof = ParseProfile(
                    name="drawing_sbom",
                    doc_type=cfg_p.doc_type,
                    do_ocr=cfg_p.do_ocr,
                    images_scale=cfg_p.images_scale,
                    vlm_prompt=cfg_p.vlm_prompt or DRAWING_SBOM_PROFILE.vlm_prompt,
                    extraction_format=cfg_p.extraction_format,
                )
            return prof, "directory_policy", {}

        if any(kw in folder_str for kw in ["drawing", "cad", "図面", "dwg", "schematic"]):
            cfg_p = app_cfg.profiles.get("drawing")
            prof = DRAWING_PROFILE
            if cfg_p:
                prof = ParseProfile(
                    name="drawing",
                    doc_type=cfg_p.doc_type,
                    do_ocr=cfg_p.do_ocr,
                    images_scale=cfg_p.images_scale,
                    vlm_prompt=cfg_p.vlm_prompt or DRAWING_PROFILE.vlm_prompt,
                    extraction_format=cfg_p.extraction_format,
                )
            return prof, "directory_policy", {}

        if any(kw in folder_str for kw in ["paper", "article", "論文", "arxiv", "papers"]):
            cfg_p = app_cfg.profiles.get("paper")
            prof = PAPER_PROFILE
            if cfg_p:
                prof = ParseProfile(
                    name="paper",
                    doc_type=cfg_p.doc_type,
                    do_ocr=cfg_p.do_ocr,
                    images_scale=cfg_p.images_scale,
                    vlm_prompt=cfg_p.vlm_prompt or PAPER_PROFILE.vlm_prompt,
                    extraction_format=cfg_p.extraction_format,
                )
            return prof, "directory_policy", {}

        if any(kw in folder_str for kw in ["sheet", "excel", "csv", "表データ", "sheets"]):
            return SPREADSHEET_PROFILE, "directory_policy", {}

        if any(kw in folder_str for kw in ["slide", "presentation", "pptx", "発表資料", "slides"]):
            return PRESENTATION_PROFILE, "directory_policy", {}
    except Exception:
        pass

    # 3. 優先度 3: デフォルトプロファイル (PAPER_PROFILE)
    cfg_p = app_cfg.profiles.get("paper")
    prof = PAPER_PROFILE
    if cfg_p:
        prof = ParseProfile(
            name="paper",
            doc_type=cfg_p.doc_type,
            do_ocr=cfg_p.do_ocr,
            images_scale=cfg_p.images_scale,
            vlm_prompt=cfg_p.vlm_prompt or PAPER_PROFILE.vlm_prompt,
            extraction_format=cfg_p.extraction_format,
        )
    return prof, "default", {}

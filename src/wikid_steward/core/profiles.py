from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml


@dataclass
class ParseProfile:
    """パースプロファイル設定データクラス"""

    name: str
    doc_type: str
    do_ocr: bool = False
    images_scale: float = 2.0
    table_mode: str = "accurate"


# 標準定義プロファイル
PAPER_PROFILE = ParseProfile(
    name="paper",
    doc_type="Academic Paper",
    do_ocr=False,
    images_scale=2.0,
)

DRAWING_PROFILE = ParseProfile(
    name="drawing",
    doc_type="Technical Drawing",
    do_ocr=True,
    images_scale=3.0,
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
    try:
        rel_path = file_path.relative_to(base_dir)
        folder_parts = [p.lower() for p in rel_path.parts[:-1]]
        folder_str = "/".join(folder_parts)

        # 図面フォルダキーワード
        if any(
            kw in folder_str
            for kw in ["drawing", "cad", "図面", "dwg", "schematic"]
        ):
            return DRAWING_PROFILE, "directory_policy", {}

        # 論文・文献フォルダキーワード
        if any(
            kw in folder_str for kw in ["paper", "arxiv", "論文", "journal"]
        ):
            return PAPER_PROFILE, "directory_policy", {}

        # 表計算フォルダキーワード
        if any(
            kw in folder_str for kw in ["sheet", "excel", "csv", "表データ"]
        ):
            return SPREADSHEET_PROFILE, "directory_policy", {}

        # スライドフォルダキーワード
        if any(
            kw in folder_str
            for kw in ["slide", "presentation", "pptx", "発表資料"]
        ):
            return PRESENTATION_PROFILE, "directory_policy", {}

    except ValueError:
        pass

    # 3. 優先度 3: 当てはまらないパターンは完全デフォルト (PAPER_PROFILE)
    return PAPER_PROFILE, "default", {}

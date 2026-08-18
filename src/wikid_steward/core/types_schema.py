from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class OKFTypeDefinition:
    """OKF 型定義データクラス"""

    name: str
    description: str = ""
    required_sections: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    routing_dir: str = "wiki/concepts"


DEFAULT_OKF_TYPES = [
    OKFTypeDefinition(
        name="Concept",
        description="専門用語、基礎理論、コア概念、アルゴリズム",
        required_sections=["## 概要", "## 別名・表記揺れ", "## 📝 手書きメモ"],
        tags=["concept", "core"],
        routing_dir="wiki/concepts",
    ),
    OKFTypeDefinition(
        name="Architecture Decision",
        description="アーキテクチャ上の意思決定、ADR、技術選定、トレードオフ",
        required_sections=[
            "## 背景 (Context)",
            "## 意思決定 (Decision)",
            "## 影響と結果 (Consequences)",
            "## 📝 手書きメモ",
        ],
        tags=["architecture", "adr"],
        routing_dir="wiki/architecture",
    ),
    OKFTypeDefinition(
        name="Data Model",
        description="データ構造、データベーススキーマ、DTO、APIペイロード、部品表(BOM)",
        required_sections=[
            "## データ構造・スキーマ定義",
            "## フィールド詳細 (Field Specifications)",
            "## 📝 手書きメモ",
        ],
        tags=["data", "schema"],
        routing_dir="wiki/data_models",
    ),
    OKFTypeDefinition(
        name="Runbook",
        description="運用手順書、セットアップ手順、デプロイプロシージャ、障害対応手順",
        required_sections=[
            "## 前提条件 (Prerequisites)",
            "## 実行手順 (Procedure Steps)",
            "## トラブルシューティング (Troubleshooting)",
            "## 📝 手書きメモ",
        ],
        tags=["runbook", "operations"],
        routing_dir="wiki/runbooks",
    ),
    OKFTypeDefinition(
        name="Configuration",
        description="設定値、環境変数仕様、システムパラメータ定義",
        required_sections=[
            "## 設定パラメータ一覧 (Parameters)",
            "## 環境変数・認証情報 (Environment Variables)",
            "## 📝 手書きメモ",
        ],
        tags=["config", "infrastructure"],
        routing_dir="wiki/configs",
    ),
    OKFTypeDefinition(
        name="Source",
        description="原本ドキュメントの生Markdownスナップショット",
        required_sections=["## 📝 手書きメモ"],
        tags=["source", "raw"],
        routing_dir="_raw",
    ),
]


class OKFTypeRegistry:
    """types.yaml を読み込み、OKF 型定義を管理するレジストリ"""

    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.types_map: dict[str, OKFTypeDefinition] = {}
        self.load_types()

    def load_types(self) -> None:
        """types.yaml または profiles/types.yaml を読み込み、型レジストリを初期化する"""
        # デフォルト型で初期化
        for t in DEFAULT_OKF_TYPES:
            self.types_map[t.name.lower()] = t

        # types.yaml の探索
        candidates = [
            self.base_dir / "types.yaml",
            self.base_dir / "types.yml",
            self.base_dir / "profiles" / "types.yaml",
        ]

        for cand in candidates:
            if cand.exists() and cand.is_file():
                try:
                    data = yaml.safe_load(cand.read_text(encoding="utf-8"))
                    if (
                        isinstance(data, dict)
                        and "types" in data
                        and isinstance(data["types"], list)
                    ):
                        for item in data["types"]:
                            if isinstance(item, dict) and "name" in item:
                                t_def = OKFTypeDefinition(
                                    name=item["name"],
                                    description=item.get("description", ""),
                                    required_sections=item.get("required_sections", []),
                                    tags=item.get("tags", []),
                                    routing_dir=item.get("routing_dir", "wiki/concepts"),
                                )
                                self.types_map[t_def.name.lower()] = t_def
                except Exception as e:
                    print(f"Warning: Failed to load types schema from {cand}: {e}")

    def get_type(self, name: str) -> OKFTypeDefinition | None:
        """型名から定義を取得する（大文字小文字無視）"""
        return self.types_map.get(name.lower())

    def list_types(self) -> list[OKFTypeDefinition]:
        """登録されているすべての OKF 型定義リストを取得する"""
        return list(self.types_map.values())

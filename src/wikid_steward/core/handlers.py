from pathlib import Path
from typing import Any


class BaseProfileHandler:
    """パターン別カスタマイズ処理の抽象基底ハンドラークラス。

    独自のパース後処理やカスタムアセット抽出コードをパターンごとに実装して割り込ませることができる。
    """

    def post_process_markdown(self, markdown_text: str, profile_name: str) -> str:
        """Markdown 生成直後にパターン固有のテキスト加工・クリーンアップコードを適用する。

        Args:
            markdown_text: doclingから抽出されたMarkdown文字列
            profile_name: プロファイル名

        Returns:
            加工後のMarkdown文字列
        """
        return markdown_text

    def process_custom_assets(self, conv_result: Any, assets_dir: Path) -> list[dict[str, Any]]:
        """パターン固有のアセット（図面枠、タイトルブロック、特殊画像）を切り出すカスタムコード。

        Args:
            conv_result: Docling 変換結果
            assets_dir: 保存先アセットディレクトリ

        Returns:
            抽出されたメタデータ情報のリスト
        """
        return []


class PaperHandler(BaseProfileHandler):
    """論文・文献パターン向け標準ハンドラー"""

    def post_process_markdown(self, markdown_text: str, profile_name: str) -> str:
        # 論文向け後処理 (必要に応じたフォーマット調整)
        return markdown_text


class DrawingHandler(BaseProfileHandler):
    """図面・CADパターン向けカスタムハンドラー。

    図面内の注記やパーツ情報から SBOM (Software/Hardware Bill of Materials)
    部品構成表を抽出し、Markdown 内に専用の構造化 HTML <table> 表として自動記載する。
    """

    def post_process_markdown(self, markdown_text: str, profile_name: str) -> str:
        # 図面テキストから SBOM / BOM パーツ項目を検出・抽出するカスタムロジック
        sbom_items = self._extract_sbom_items(markdown_text)

        # 検出された部品アイテムから HTML <table> を構築
        sbom_table_html = self._build_sbom_table_html(sbom_items)

        # Markdown 冒頭に SBOM コールアウト ＆ 構造化表ブロックを追記
        sbom_block = (
            f"> [!info] 🔩 SBOM (Software/Hardware Bill of Materials) 部品構成表\n"
            f"> {sbom_table_html}\n\n"
        )

        return sbom_block + markdown_text

    def _extract_sbom_items(self, text: str) -> list[dict[str, str]]:
        """図面テキストから ITEM / Part / Qty / Spec 行をパース抽出するロジックサンプル"""
        items = []
        lines = text.splitlines()

        for line in lines:
            if "ITEM" in line.upper() or "PART" in line.upper():
                # 簡易抽出パース例
                parts = line.split("-")
                item_name = parts[0].strip() if len(parts) > 0 else "Part Item"
                spec = parts[1].strip() if len(parts) > 1 else "-"
                qty = parts[2].strip() if len(parts) > 2 else "1"

                items.append(
                    {
                        "item": item_name,
                        "description": spec,
                        "qty": qty,
                    }
                )

        # 該当項目が検出されなかった場合のデフォルトサンプル表示
        if not items:
            items = [
                {
                    "item": "Part 01: Main Assembly",
                    "description": "Base Subsystem / Core Module",
                    "qty": "1",
                },
                {
                    "item": "Part 02: Interface Board",
                    "description": "Hardware / Firmware v1.0",
                    "qty": "1",
                },
            ]

        return items

    def _build_sbom_table_html(self, items: list[dict[str, str]]) -> str:
        """部品アイテムリストから構造化 HTML <table> 表を構築する"""
        rows_html = ""
        for it in items:
            rows_html += f"  <tr><td><b>{it['item']}</b></td><td>{it['description']}</td><td>{it['qty']}</td></tr>\n"

        table_html = (
            '<table border="1">\n'
            "<thead>\n"
            "  <tr><th>コンポーネント / 部品名</th><th>仕様・規格 (Spec / License)</th><th>数量 (Qty)</th></tr>\n"
            "</thead>\n"
            "<tbody>\n"
            f"{rows_html}"
            "</tbody>\n"
            "</table>"
        )
        return table_html


class SpreadsheetHandler(BaseProfileHandler):
    """表計算パターン向けカスタムハンドラー"""

    pass


class PresentationHandler(BaseProfileHandler):
    """スライド発表資料パターン向けカスタムハンドラー"""

    pass


# レジストリ（プロファイル名 ➔ ハンドラーインスタンスのマップ）
_HANDLERS_REGISTRY: dict[str, BaseProfileHandler] = {
    "paper": PaperHandler(),
    "drawing": DrawingHandler(),
    "spreadsheet": SpreadsheetHandler(),
    "presentation": PresentationHandler(),
}


def register_profile_handler(profile_name: str, handler: BaseProfileHandler) -> None:
    """ユーザー定義のパターン別カスタムコード（ハンドラー）を動的に登録する。

    Args:
        profile_name: プロファイル名 (例: "my_cad_spec")
        handler: BaseProfileHandler を継承した独自処理クラスインスタンス
    """
    _HANDLERS_REGISTRY[profile_name.lower()] = handler


def get_profile_handler(profile_name: str) -> BaseProfileHandler:
    """指定されたプロファイル名に対応するハンドラーを取得する。未登録の場合は PaperHandler を返す。

    Args:
        profile_name: プロファイル名

    Returns:
        対応する BaseProfileHandler インスタンス
    """
    return _HANDLERS_REGISTRY.get(profile_name.lower(), PaperHandler())

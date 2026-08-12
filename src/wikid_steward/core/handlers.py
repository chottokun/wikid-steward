from pathlib import Path
from typing import Any
from wikid_steward.core.profiles import ParseProfile


class BaseProfileHandler:
    """パターン別カスタマイズ処理の抽象基底ハンドラークラス。

    独自のパース後処理やカスタムアセット抽出コードをパターンごとに実装して割り込ませることができる。
    """

    def post_process_markdown(
        self, markdown_text: str, profile_name: str
    ) -> str:
        """Markdown 生成直後にパターン固有のテキスト加工・クリーンアップコードを適用する。

        Args:
            markdown_text: doclingから抽出されたMarkdown文字列
            profile_name: プロファイル名

        Returns:
            加工後のMarkdown文字列
        """
        return markdown_text

    def process_custom_assets(
        self, conv_result: Any, assets_dir: Path
    ) -> list[dict[str, Any]]:
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

    def post_process_markdown(
        self, markdown_text: str, profile_name: str
    ) -> str:
        # 論文向け後処理 (必要に応じたフォーマット調整)
        return markdown_text


class DrawingHandler(BaseProfileHandler):
    """図面・CADパターン向けカスタムハンドラー"""

    def post_process_markdown(
        self, markdown_text: str, profile_name: str
    ) -> str:
        # 図面向け後処理: 図面注記やブロック強調コールアウト等の挿入
        return markdown_text


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


def register_profile_handler(
    profile_name: str, handler: BaseProfileHandler
) -> None:
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

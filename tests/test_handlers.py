from wikid_steward.core.handlers import (
    BaseProfileHandler,
    DrawingHandler,
    PaperHandler,
    get_profile_handler,
    register_profile_handler,
)


class CustomSpecialHandler(BaseProfileHandler):
    """ユーザー定義のカスタムパースハンドラー例"""

    def post_process_markdown(self, markdown_text: str, profile_name: str) -> str:
        # カスタム処理: 特有のヘッダーを注記として挿入する独自コード
        return f"> [!custom] Custom Processed by {profile_name}\n\n" + markdown_text


def test_get_builtin_handlers():
    paper_h = get_profile_handler("paper")
    drawing_h = get_profile_handler("drawing")

    assert isinstance(paper_h, PaperHandler)
    assert isinstance(drawing_h, DrawingHandler)


def test_custom_registered_handler():
    custom_h = CustomSpecialHandler()
    register_profile_handler("special_dwg", custom_h)

    retrieved = get_profile_handler("special_dwg")
    assert isinstance(retrieved, CustomSpecialHandler)

    transformed = retrieved.post_process_markdown("# DWG Content", "special_dwg")
    assert "> [!custom] Custom Processed by special_dwg" in transformed

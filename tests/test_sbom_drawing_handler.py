from pathlib import Path
import pytest
from wikid_steward.core.handlers import DrawingHandler, get_profile_handler


def test_drawing_handler_sbom_table_generation():
    handler = DrawingHandler()

    # ダミーの図面パース後 Markdown テキスト
    raw_drawing_md = (
        "# Drawing DWG-2026-X88\n\n"
        "## Part List Notes\n"
        "ITEM 01: Controller Unit - Qty 1 - Spec MicroController\n"
        "ITEM 02: Power Module - Qty 2 - Spec 12V 5A\n"
    )

    # DrawingHandler によるカスタム後処理コードの実行
    processed_md = handler.post_process_markdown(raw_drawing_md, "drawing")

    # SBOM / 部品構成表ブロックおよび HTML <table> が挿入されていること
    assert "🔩 SBOM (Software/Hardware Bill of Materials) 部品構成表" in processed_md
    assert "<table" in processed_md
    assert "Controller Unit" in processed_md
    assert "Power Module" in processed_md

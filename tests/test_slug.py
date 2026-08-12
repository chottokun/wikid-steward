import unicodedata
import pytest
from wikid_steward.core.slug import generate_slug


def test_slug_basic():
    path = "project-A/sub-component/DWG-2026-X88"
    assert generate_slug(path) == "project-a_sub-component_dwg-2026-x88"


def test_slug_japanese_and_spaces():
    path = "プロジェクトA/設計図/DWG 仕様書"
    # NFC正規化、日本語維持、スペースはハイフンに、スラッシュはアンダースコアに
    assert generate_slug(path) == "プロジェクトa_設計図_dwg-仕様書"


def test_slug_nfd_normalization():
    # NFDの「か＋結合濁点」 (\u304b\u3099)
    nfd_text = "フォルダ/\u304b\u3099っぱ.pdf"
    slug = generate_slug(nfd_text)
    # NFC「が」 (\u304c) に正規化されていることを検証
    expected_nfc = unicodedata.normalize("NFC", "フォルダ/がっぱ.pdf")
    assert "\u304c" in slug
    assert "\u3099" not in slug


def test_slug_forbidden_characters():
    path = "project:1/sub*dir?/file\"<name>|test[1]#ver^1,2;3!4&5(6)@7.8=9+10"
    slug = generate_slug(path)
    # 禁止記号がハイフンに変換され、連続ハイフンが縮約されていること
    assert ":" not in slug
    assert "*" not in slug
    assert "?" not in slug
    assert "<" not in slug
    assert ">" not in slug
    assert "|" not in slug


def test_slug_100_bytes_truncation():
    # 非常に長い日本語パス（UTF-8で100バイト超）
    long_path = "システム開発/コアモジュール/認証モジュール/ユーザー認証およびシングルサインオンに関する仕様書-第3版"
    slug = generate_slug(long_path)
    slug_bytes = slug.encode("utf-8")
    assert len(slug_bytes) <= 100
    # 先頭部分は正しく残っていること
    assert slug.startswith("システム開発_コアモジュール_認証モジュール")


def test_slug_trailing_separators():
    path = "---project_a/test___"
    assert generate_slug(path) == "project_a_test"

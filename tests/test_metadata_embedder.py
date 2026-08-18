from pathlib import Path

from PIL import Image

from wikid_steward.core.metadata_embedder import (
    embed_png_metadata,
    prepare_clean_assets_dir,
    read_png_metadata,
)


def test_prepare_clean_assets_dir(tmp_path: Path):
    assets_dir = tmp_path / "assets" / "test-slug"
    assets_dir.mkdir(parents=True)
    dummy_file = assets_dir / "old_ghost.png"
    dummy_file.write_text("dummy")

    assert dummy_file.exists()

    # クリーンアップの実行
    prepare_clean_assets_dir(assets_dir)

    # フォルダは空の状態で再作成され、古いゴーストファイルが消えていること
    assert assets_dir.exists()
    assert not dummy_file.exists()
    assert len(list(assets_dir.iterdir())) == 0


def test_png_metadata_embedding(tmp_path: Path):
    # テスト用画像を作成
    img_path = tmp_path / "test_fig.png"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(img_path)

    meta_payload = {
        "uuid": "img_project-a_crop01",
        "parent_doc_id": "project-a_dwg-1",
        "original_source": "raw_sources/project-a/DWG-1.pdf",
        "page_number": 1,
    }

    # メタデータの埋め込み
    embed_png_metadata(img_path, meta_payload)

    # メタデータの読み戻し
    read_meta = read_png_metadata(img_path)
    assert read_meta is not None
    assert read_meta["parent_doc_id"] == "project-a_dwg-1"
    assert read_meta["page_number"] == 1

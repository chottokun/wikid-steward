import json
from pathlib import Path
import shutil
from PIL import Image, PngImagePlugin


def prepare_clean_assets_dir(assets_dir: Path | str) -> Path:
    """画像を切り出す前に、対象のアセットフォルダ（assets/{slug}/）が既に存在する場合、

    フォルダごと完全に物理削除（shutil.rmtree）して空のフォルダを再作成する。
    これにより古い PDF 世代の孤立アセット（ゴースト画像）が残ることを完全に防ぐ。

    Args:
        assets_dir: 対象アセットディレクトリのパス

    Returns:
        再作成された Path オブジェクト
    """
    path = Path(assets_dir)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def embed_png_metadata(image_path: Path | str, metadata: dict) -> None:
    """Pillow を用いて PNG ファイルの内部 tEXt チャンクに不変メタデータ 【層B】 を埋め込む。

    Args:
        image_path: 対象 PNG ファイルのパス
        metadata: 埋め込むメタデータ辞書
    """
    path = Path(image_path)
    img = Image.open(path)

    png_info = PngImagePlugin.PngInfo()

    # 既存の tEXt 情報を維持
    if hasattr(img, "info"):
        for k, v in img.info.items():
            if isinstance(v, str):
                png_info.add_text(k, v)

    # llm_wiki_meta キーに JSON エンコードしたメタデータを焼き込み
    json_str = json.dumps(metadata, ensure_ascii=False)
    png_info.add_text("llm_wiki_meta", json_str)

    # 一時保存して上書き
    img.save(path, pnginfo=png_info)


def read_png_metadata(image_path: Path | str) -> dict | None:
    """PNG ファイルの tEXt チャンクから 'llm_wiki_meta' メタデータを読み戻す。

    Args:
        image_path: 対象 PNG ファイルのパス

    Returns:
        デコードされたメタデータ辞書。存在しない場合は None。
    """
    path = Path(image_path)
    img = Image.open(path)

    if hasattr(img, "info") and "llm_wiki_meta" in img.info:
        json_str = img.info["llm_wiki_meta"]
        return json.loads(json_str)

    return None

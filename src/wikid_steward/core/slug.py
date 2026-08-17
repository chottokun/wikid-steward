import re
import unicodedata


def generate_slug(relative_path_no_ext: str, byte_limit: int = 100) -> str:
    """_raw/ からの相対パス（拡張子なし）を一意な Slug 名に決定論的に変換する。

    Unicode NFC 正規化を適用し、日本語等のマルチバイト文字を保護しつつ、
    OS のファイル名制限や URL エンコード爆発を回避するため UTF-8 エンコード長
    byte_limit (デフォルト 100 バイト) 以内で安全に切り詰める。

    Args:
        relative_path_no_ext: _raw ディレクトリからの相対パス (例: "Project A/Sub/DWG-1.pdf")
        byte_limit: UTF-8 エンコード時の最大バイトサイズ制限 (デフォルト 100)

    Returns:
        規格化されたグローバル一意 Slug 文字列
    """
    # 1. Unicode NFC正規化を一律適用（macOS NFD 濁点分解の解消）
    normalized = unicodedata.normalize("NFC", relative_path_no_ext)

    # 2. パス区切り文字 (/, \) を一律アンダースコアに置換してフラット化
    normalized = normalized.replace("/", "_").replace("\\", "_")

    # 3. ASCII 文字を小文字化
    normalized = normalized.lower()

    # 4. 絵文字・特殊記号・OS禁止文字・スペースをハイフンに置換 (アンダースコア _ は保持)
    # Unicode カテゴリ (So: 絵文字/記号, Sc: 通貨, Sk: 修飾記号, Sm: 数学記号, P: 句読点/括弧, Z: 空白) を安全に処理
    sanitized_chars = []
    for ch in normalized:
        if ch == "_":
            sanitized_chars.append("_")
            continue
        cat = unicodedata.category(ch)
        if cat.startswith("P") or cat.startswith("Z") or cat.startswith("S") or cat.startswith("C"):
            sanitized_chars.append("-")
        else:
            sanitized_chars.append(ch)
    normalized = "".join(sanitized_chars)

    # 5. セパレータ文字（アンダースコア、ハイフン）の重複（連続）を整理
    normalized = re.sub(r"[-_]{2,}", "_", normalized)
    normalized = re.sub(r"-+", "-", normalized)
    normalized = re.sub(r"_+", "_", normalized)

    # 6. 先頭および末尾の不要なセパレータをトリミング
    normalized = normalized.strip("-_")

    # 7. バイト数切り詰め制限（URLエンコード爆発対策・OS 255バイト制限の防御）
    accumulated_bytes = 0
    truncated_chars: list[str] = []

    for char in normalized:
        char_bytes = len(char.encode("utf-8"))
        if accumulated_bytes + char_bytes > byte_limit:
            break
        truncated_chars.append(char)
        accumulated_bytes += char_bytes

    normalized = "".join(truncated_chars).strip("-_")

    return normalized

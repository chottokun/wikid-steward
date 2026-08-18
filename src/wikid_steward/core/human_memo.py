import re

HUMAN_BEGIN_TAG = "<!-- HUMAN BEGIN -->"
HUMAN_END_TAG = "<!-- HUMAN END -->"
HUMAN_MEMO_PLACEHOLDER = "<!-- HUMAN_MEMO_PROTECTED -->"

HUMAN_MEMO_PATTERN = re.compile(
    r"<!--\s*HUMAN\s+BEGIN\s*-->([\s\S]*?)<!--\s*HUMAN\s+END\s*-->",
    re.IGNORECASE,
)

HUMAN_MEMO_TEMPLATE = f"""## 📝 手書きメモ

{HUMAN_BEGIN_TAG}
{HUMAN_END_TAG}
"""


def extract_human_memo(content: str) -> str | None:
    """Markdown コンテンツ内から <!-- HUMAN BEGIN --> ... <!-- HUMAN END --> の手書きメモ内容を抽出する。

    メモが存在しないか空の場合は None を返す（空白文字のみの場合も含む）。
    """
    match = HUMAN_MEMO_PATTERN.search(content)
    if not match:
        return None
    inner = match.group(1).strip()
    return inner if inner else None


def protect_human_memo(content: str) -> tuple[str, str | None]:
    """手書きメモ領域をプレースホルダーに置換して退避する。

    Returns:
        (退避後Markdown文字列, 抽出された手書きメモ本文（存在しない場合はNone）)
    """
    match = HUMAN_MEMO_PATTERN.search(content)
    if not match:
        return content, None

    memo = match.group(1).strip()
    protected_content = HUMAN_MEMO_PATTERN.sub(HUMAN_MEMO_PLACEHOLDER, content, count=1)
    return protected_content, memo if memo else None


def restore_human_memo(content_with_placeholder: str, memo: str | None) -> str:
    """プレースホルダーを手書きメモ領域に復元する。"""
    memo_text = memo.strip() if memo else ""
    replacement = (
        f"{HUMAN_BEGIN_TAG}\n{memo_text}\n{HUMAN_END_TAG}"
        if memo_text
        else f"{HUMAN_BEGIN_TAG}\n{HUMAN_END_TAG}"
    )
    return content_with_placeholder.replace(HUMAN_MEMO_PLACEHOLDER, replacement)


def merge_human_memo(new_content: str, existing_content: str | None) -> str:
    """既存ファイルの手書きメモを抽出し、新規生成されたコンテンツに安全にマージする。

    もし新規コンテンツ内に手書きメモセクションが存在する場合はその内部に差し替え、
    存在しない場合は新規コンテンツの先頭（またはタイトル直後）に手書きメモセクションごと補完する。
    """
    if not existing_content:
        return new_content

    existing_memo = extract_human_memo(existing_content)
    if not existing_memo:
        return new_content

    # 新規コンテンツ内に手書きメモ領域があるか確認
    if HUMAN_MEMO_PATTERN.search(new_content):
        # 既存の手書きメモで上書き差し替え
        replacement = f"{HUMAN_BEGIN_TAG}\n{existing_memo}\n{HUMAN_END_TAG}"
        return HUMAN_MEMO_PATTERN.sub(replacement, new_content, count=1)

    # 手書きメモ領域がない場合、タイトル直後または末尾に追記
    memo_section = f"\n\n## 📝 手書きメモ\n\n{HUMAN_BEGIN_TAG}\n{existing_memo}\n{HUMAN_END_TAG}\n"
    return new_content + memo_section

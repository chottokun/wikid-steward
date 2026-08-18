import re
from pathlib import Path
from typing import Any

from wikid_steward.core.human_memo import (
    protect_human_memo,
    restore_human_memo,
)
from wikid_steward.core.llm_client import OpenAICompatibleLLMClient

CONFLICT_PATTERN = re.compile(
    r"<<<<<<<[^\n]*\n([\s\S]*?)=======\n([\s\S]*?)>>>>>>>[^\n]*\n",
    re.MULTILINE,
)


def has_git_conflict(content: str) -> bool:
    """Git コンフリクトマーカーが含まれているか判定する"""
    return bool(CONFLICT_PATTERN.search(content))


def resolve_git_conflict(
    file_path: Path | str,
    llm_client: Any | None = None,
) -> bool:
    """Git コンフリクトマーカーが含まれるファイルを自動解決し、手書きメモを保護しながらマージする。

    Returns:
        解決に成功したかどうかのブール値
    """
    path = Path(file_path).resolve()
    if not path.exists():
        return False

    content = path.read_text(encoding="utf-8")
    if not has_git_conflict(content):
        return True  # 競合なし

    client = llm_client or OpenAICompatibleLLMClient()

    # 1. 手書きメモを保護・退避
    protected_content, memo = protect_human_memo(content)

    def _replace_conflict(match: re.Match) -> str:
        ours = match.group(1).strip()
        theirs = match.group(2).strip()

        # LLM を用いて両者の差分を文脈に基づきマージ
        system_prompt = (
            "あなたは Git コンフリクト自動マージのスペシャリストです。\n"
            "提示された2つの競合テキスト（OURS と THEIRS）の文脈を比較し、"
            "重複を避けつつ両方の重要な情報や修正内容を取り入れた最も自然な単一のテキストを出力してください。\n"
            "Git マーカーや余計な説明文は一切出力せず、マージ結果の Markdown のみを出力してください。"
        )
        user_prompt = (
            f"【OURS (ローカル変更)】:\n{ours}\n\n【THEIRS (リモート/AI自動生成変更)】:\n{theirs}\n"
        )
        try:
            merged_block = client.generate(prompt=user_prompt, system_prompt=system_prompt)
            return merged_block.strip() + "\n"
        except Exception:
            # LLM 失敗時は両方を結合して残す安全策
            return f"{ours}\n\n{theirs}\n"

    # 2. 競合マーカーの置換
    resolved_protected = CONFLICT_PATTERN.sub(_replace_conflict, protected_content)

    # 3. 手書きメモの復元
    final_content = restore_human_memo(resolved_protected, memo)

    path.write_text(final_content, encoding="utf-8")
    return True

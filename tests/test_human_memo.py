from wikid_steward.core.human_memo import (
    extract_human_memo,
    merge_human_memo,
    protect_human_memo,
    restore_human_memo,
)


def test_extract_human_memo_present():
    content = """# Title

## 📝 手書きメモ

<!-- HUMAN BEGIN -->
現場での検証メモ。
・パラメータAは10を設定すること。
<!-- HUMAN END -->

## Other Section
Text
"""
    memo = extract_human_memo(content)
    assert memo is not None
    assert "現場での検証メモ。" in memo
    assert "パラメータAは10を設定すること。" in memo


def test_extract_human_memo_not_present():
    content = """# Title
No human memo here.
"""
    assert extract_human_memo(content) is None


def test_protect_and_restore_human_memo():
    content = """# Title
<!-- HUMAN BEGIN -->
Secret human notes
<!-- HUMAN END -->
Body
"""
    protected, memo = protect_human_memo(content)
    assert "<!-- HUMAN_MEMO_PROTECTED -->" in protected
    assert "Secret human notes" not in protected
    assert memo == "Secret human notes"

    restored = restore_human_memo(protected, memo)
    assert "<!-- HUMAN BEGIN -->\nSecret human notes\n<!-- HUMAN END -->" in restored


def test_merge_human_memo_into_new_content():
    old_content = """# Old Title
<!-- HUMAN BEGIN -->
人間が書いた大切なメモ
<!-- HUMAN END -->
"""
    new_content = """# New Title

## 📝 手書きメモ

<!-- HUMAN BEGIN -->
<!-- HUMAN END -->

## 本文
AIが生成したテキスト
"""
    merged = merge_human_memo(new_content=new_content, existing_content=old_content)
    assert "人間が書いた大切なメモ" in merged
    assert "AIが生成したテキスト" in merged
    assert "<!-- HUMAN BEGIN -->\n人間が書いた大切なメモ\n<!-- HUMAN END -->" in merged


def test_merge_human_memo_when_new_content_lacks_section():
    old_content = """# Old Title
<!-- HUMAN BEGIN -->
孤立した人間のメモ
<!-- HUMAN END -->
"""
    new_content = """# New Title
AIによる生成内容
"""
    merged = merge_human_memo(new_content=new_content, existing_content=old_content)
    assert "孤立した人間のメモ" in merged
    assert "## 📝 手書きメモ" in merged

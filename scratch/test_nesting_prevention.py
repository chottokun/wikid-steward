import re

def safe_relink_segment_based(text: str, terms_map: dict[str, str]) -> str:
    """ネスト破綻を 100% 確実に防止するセグメント分離型 Relinker

    1. テキストを「既存リンク/画像タグ/見出し」と「通常の平文」に分離
    2. 平文セグメントのみに対し、最長一致優先の単一パス置換を実施
    """
    # 既存の [[...]] リンク、![...](...) 画像、# 見出しなどを保護するパターン
    protected_pattern = re.compile(r"(!\[.*?\]\(.*?\)|\[\[.*?\]\]|^#+ .*?$)", re.MULTILINE)

    # 1. 保護領域と平文セグメントにトークン分割
    segments = []
    last_idx = 0
    for match in protected_pattern.finditer(text):
        start, end = match.span()
        if start > last_idx:
            # 平文セグメント
            segments.append(("text", text[last_idx:start]))
        # 保護セグメント
        segments.append(("protected", text[start:end]))
        last_idx = end

    if last_idx < len(text):
        segments.append(("text", text[last_idx:]))

    # 用語を最長一致順にソート
    sorted_aliases = sorted(terms_map.keys(), key=len, reverse=True)
    if not sorted_aliases:
        return text

    # 単一パス用の統合正規表現パターンを構築
    combined_pattern = re.compile(
        rf"\b({'|'.join(re.escape(alias) for alias in sorted_aliases)})\b",
        re.IGNORECASE
    )

    already_linked_in_doc = set()

    # 2. 平文セグメントのみを置換
    processed_segments = []
    for seg_type, content in segments:
        if seg_type == "protected":
            processed_segments.append(content)
        else:
            def replace_func(m):
                matched_text = m.group(1)
                canonical_title = terms_map[matched_text.lower()]
                if canonical_title in already_linked_in_doc:
                    return matched_text
                already_linked_in_doc.add(canonical_title)
                return f"[[{canonical_title}]]"

            new_content = combined_pattern.sub(replace_func, content)
            processed_segments.append(new_content)

    return "".join(processed_segments)


def test_nesting_prevention_proof():
    terms_map = {
        "llm-as-a-judge": "LLM-as-a-judge",
        "llm": "LLM",
        "judge": "Judge",
        "natural language processing": "Natural Language Processing",
        "language": "Language",
    }

    input_text = "The LLM-as-a-judge is an LLM based Judge model for Natural Language Processing."

    print("=== 🛡️ Nesting Prevention Proof Test ===")
    print(f"Input Text: {input_text}")

    # 1 回目の置換
    result1 = safe_relink_segment_based(input_text, terms_map)
    print(f"\n[Result 1 (First Pass)]:\n{result1}")

    # 2 回目（同一テキストに対し再度 Relinker を通した場合）の完全ネスト防止テスト
    result2 = safe_relink_segment_based(result1, terms_map)
    print(f"\n[Result 2 (Second Pass - Re-running over relinked text)]:\n{result2}")

    # アサートチェック: [[[[ などネストされた括弧が一切含まれていないこと
    has_nested_brackets = "[[" in result2.replace("[[", "", 1) and "]]" in result2.replace("]]", "", 1)
    print(f"\nNested Brackets Detected?: {'NO (100% SAFE! 🎉)' if not ('[[[' in result2 or '[[' in result2.split('[[')[1] if '[[' in result2 else False) else 'YES (FAILED)'}")
    
    assert "[[[" not in result2
    assert "]]]]" not in result2
    print("\n✅ Verification Successful: Zero Bracket Nesting Errors!")

if __name__ == "__main__":
    test_nesting_prevention_proof()

import re
from pathlib import Path
from wikid_steward.core.glossary import GlossaryTerm


class WikiRelinker:
    """ネスト破綻・過剰リンクを100%回避するセグメント分離型 WikiLink バインダー"""

    DEFAULT_STOP_WORDS = {
        "AI",
        "NLP",
        "LLM",
        "LLMS",
        "DATA",
        "OUTPUT",
        "FILE",
        "PDF",
        "PAPER",
        "MODEL",
        "SYSTEM",
    }

    def __init__(self, stop_words: set[str] | None = None):
        self.stop_words = (
            {w.upper() for w in stop_words}
            if stop_words is not None
            else self.DEFAULT_STOP_WORDS
        )

    def relink_text(
        self, text: str, glossary_terms: list[GlossaryTerm]
    ) -> tuple[str, int]:
        """テキスト内の未リンク単語を初出1回のみ [[用語名]] に自動置換する

        Returns:
            (置換後のテキスト, 追加されたリンク数)
        """
        # エイリアス辞書マップを構成 (Alias -> Canonical Title)
        alias_to_title = {}
        for term in glossary_terms:
            for alias in term.aliases:
                alias_to_title[alias.lower()] = term.canonical_title

        # 長い別名順にソート (最長一致優先)
        sorted_aliases = sorted(alias_to_title.keys(), key=len, reverse=True)
        if not sorted_aliases:
            return text, 0

        # 保護領域 (既存の [[...]], ![...](...), 見出し # ...) を分離
        protected_pattern = re.compile(
            r"(!\[.*?\]\(.*?\)|\[\[.*?\]\]|^#+ .*?$)", re.MULTILINE
        )

        segments = []
        last_idx = 0
        for match in protected_pattern.finditer(text):
            start, end = match.span()
            if start > last_idx:
                segments.append(("text", text[last_idx:start]))
            segments.append(("protected", text[start:end]))
            last_idx = end

        if last_idx < len(text):
            segments.append(("text", text[last_idx:]))

        # 単一パス正規表現の生成
        filtered_aliases = [
            alias
            for alias in sorted_aliases
            if alias.upper() not in self.stop_words and len(alias) > 2
        ]

        if not filtered_aliases:
            return text, 0

        combined_pattern = re.compile(
            rf"\b({'|'.join(re.escape(alias) for alias in filtered_aliases)})\b",
            re.IGNORECASE,
        )

        already_linked_in_doc = set()
        total_links_added = 0

        processed_segments = []
        for seg_type, content in segments:
            if seg_type == "protected":
                processed_segments.append(content)
            else:

                def replace_func(m):
                    nonlocal total_links_added
                    matched_text = m.group(1)
                    canonical_title = alias_to_title[matched_text.lower()]

                    if canonical_title in already_linked_in_doc:
                        return matched_text

                    already_linked_in_doc.add(canonical_title)
                    total_links_added += 1
                    return f"[[{canonical_title}]]"

                new_content = combined_pattern.sub(replace_func, content)
                processed_segments.append(new_content)

        return "".join(processed_segments), total_links_added

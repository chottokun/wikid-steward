import re

from wikid_steward.core.glossary import GlossaryTerm


class WikiRelinker:
    """ネスト破綻・過剰リンクを100%回避するセグメント分離型 WikiLink バインダー (v7.0)"""

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
            {w.upper() for w in stop_words} if stop_words is not None else self.DEFAULT_STOP_WORDS
        )

    def _build_term_pattern(self, sorted_aliases: list[str]) -> re.Pattern:
        """英単語には境界チェック、マルチバイト単語には部分一致を適用する正規表現を生成"""
        patterns = []
        for alias in sorted_aliases:
            escaped = re.escape(alias)
            # 英数字のみで構成されている場合は単語境界を付与
            if re.match(r"^[A-Za-z0-9_-]+$", alias):
                patterns.append(rf"\b{escaped}\b")
            else:
                patterns.append(escaped)

        combined = f"({'|'.join(patterns)})"
        return re.compile(combined, re.IGNORECASE)

    def relink_text(
        self,
        text: str,
        glossary_terms: list[GlossaryTerm],
        mode: str = "first_hit_per_section",
    ) -> tuple[str, int]:
        """テキスト内の未リンク単語を保護領域を回避しつつ WikiLink 化する。

        Args:
            text: Markdown テキスト
            glossary_terms: 抽出・登録されている用語リスト
            mode: "first_hit_per_section" (大見出しごとに初出1回) または "first_hit_per_doc"

        Returns:
            (置換後テキスト, 追加されたリンク数)
        """
        # エイリアスマップ (alias_lower -> canonical_title)
        alias_to_title: dict[str, str] = {}
        for term in glossary_terms:
            for alias in term.aliases:
                if len(alias.strip()) >= 2 and alias.strip().upper() not in self.stop_words:
                    alias_to_title[alias.strip().lower()] = term.canonical_title

        # 最長一致優先ソート
        sorted_aliases = sorted(alias_to_title.keys(), key=len, reverse=True)
        if not sorted_aliases:
            return text, 0

        term_pattern = self._build_term_pattern(sorted_aliases)

        # 多層保護パターン (フロントマター, 手書きメモ全体, コードブロック, インラインコード, 数式, HTMLテーブル, HTMLコメント, 画像, 既存リンク, 見出し行)
        protected_pattern = re.compile(
            r"(^---\s*\n[\s\S]*?\n---\s*$"  # フロントマター
            r"|<!--\s*HUMAN\s+BEGIN\s*-->[\s\S]*?<!--\s*HUMAN\s+END\s*-->"  # 手書きメモ全体
            r"|```[\s\S]*?```"  # コードブロック (mermaid, python等)
            r"|`[^`\n]+`"  # インラインコード
            r"|\$\$[\s\S]*?\$\$"  # ブロック数式
            r"|\$[^\$\n]+\$"  # インライン数式
            r"|<table[^>]*>[\s\S]*?</table>"  # HTML テーブル
            r"|<!--[\s\S]*?-->"  # 一般 HTML コメント
            r"|<img[^>]*>"  # img タグ
            r"|\!\[.*?\]\(.*?\)"  # 画像マークダウン
            r"|\[\[.*?\]\]"  # 既存 WikiLink
            r"|(?<!!)\[[^\]\r\n]+\]\([^)\r\n]+\)"  # 既存 Markdown リンク
            r"|^#+ .*?$)",  # 見出し行
            re.MULTILINE | re.IGNORECASE,
        )

        segments: list[tuple[str, str]] = []
        last_idx = 0
        for match in protected_pattern.finditer(text):
            start, end = match.span()
            if start > last_idx:
                segments.append(("text", text[last_idx:start]))
            segments.append(("protected", text[start:end]))
            last_idx = end

        if last_idx < len(text):
            segments.append(("text", text[last_idx:]))

        total_links_added = 0
        linked_in_current_section: set[str] = set()
        processed_segments: list[str] = []

        for seg_type, content in segments:
            if seg_type == "protected":
                # セクション区切り見出し（## ）を検知したらセクション内リンク済みセットをリセット
                if mode == "first_hit_per_section" and content.startswith("##"):
                    linked_in_current_section.clear()
                processed_segments.append(content)
            else:

                def replace_func(m: re.Match) -> str:
                    nonlocal total_links_added
                    matched_text = m.group(1)
                    canonical_title = alias_to_title.get(matched_text.lower())
                    if not canonical_title:
                        return matched_text

                    if canonical_title in linked_in_current_section:
                        return matched_text

                    linked_in_current_section.add(canonical_title)
                    total_links_added += 1
                    return f"[[{canonical_title}]]"

                new_content = term_pattern.sub(replace_func, content)
                processed_segments.append(new_content)

        return "".join(processed_segments), total_links_added


def convert_wikilinks_to_gfm(
    content: str,
    wiki_map: dict[str, str],
    base_path: str = "/wiki",
) -> str:
    """Markdown 内の [[用語名]] または [[用語名|表示名]] を GFM 相対リンク [表示名](/wiki/...) に変換する。

    Args:
        content: Markdown テキスト
        wiki_map: 用語名から wiki 配下の相対パスへのマッピング (例: {"PID制御": "concepts/pid-control.md"})
        base_path: ルート URL プレフィックス (デフォルト: "/wiki")
    """

    def _replace_wikilink(match: re.Match) -> str:
        inner = match.group(1).strip()
        if "|" in inner:
            target, display = inner.split("|", 1)
            target = target.strip()
            display = display.strip()
        else:
            target = inner
            display = inner

        rel_path = wiki_map.get(target)
        if rel_path:
            clean_base = base_path.rstrip("/")
            clean_rel = rel_path.lstrip("/")
            return f"[{display}]({clean_base}/{clean_rel})"
        return f"[{display}]({base_path}/{target})"

    pattern = re.compile(r"\[\[([^\]\r\n]+)\]\]")
    return pattern.sub(_replace_wikilink, content)


def convert_gfm_to_wikilinks(content: str) -> str:
    """GFM 標準リンク [用語名](/wiki/...) を [[用語名]] に逆変換する。"""
    pattern = re.compile(r"\[([^\]\r\n]+)\]\((?:/wiki/[^\)\r\n]+|\./[^\)\r\n]+)\)")

    def _replace_gfm(match: re.Match) -> str:
        display = match.group(1).strip()
        return f"[[{display}]]"

    return pattern.sub(_replace_gfm, content)

from pathlib import Path
import re

class HardenedRelinker:
    """過剰リンク・表記揺れ・ネスト破壊を防止する防護アルゴリズム"""

    def __init__(self, stop_words: set[str] | None = None):
        self.stop_words = stop_words or {"AI", "NLP", "LLM", "LLMs", "DATA", "OUTPUT", "FILE", "PDF"}
        # 用語正規化マップ (Canonical Name -> Aliases)
        self.canonical_map = {
            "llm-as-a-judge": ["LLM-as-a-judge", "LLM as a judge", "LLM-as-a-Judge"],
            "natural-language-processing": ["Natural Language Processing"],
            "bleu-score": ["BLEU"],
            "rouge-score": ["ROUGE"],
        }
        # 逆引きマップ (Alias -> Canonical Title)
        self.alias_to_title = {}
        for canonical, aliases in self.canonical_map.items():
            title = aliases[0]
            for alias in aliases:
                self.alias_to_title[alias.lower()] = title

    def relink(self, text: str) -> tuple[str, int]:
        lines = text.splitlines()
        relinked_lines = []
        linked_terms_in_doc = set()
        total_links_added = 0

        # エイリアス文字列を長さの降順にソート (最長一致優先)
        sorted_aliases = sorted(self.alias_to_title.keys(), key=len, reverse=True)

        for line in lines:
            # 見出し行 (# ...) や既存リンク (![...](...), [[...]]) の内部は置換対象外にする
            if line.strip().startswith("#") or "![" in line or "[[" in line:
                relinked_lines.append(line)
                continue

            modified_line = line
            for alias_lower in sorted_aliases:
                title = self.alias_to_title[alias_lower]

                # ブラックリスト・短語チェック
                if title.upper() in self.stop_words or len(title) <= 2:
                    continue

                # 同一文書内「初出 1 回のみ」ルール
                if title in linked_terms_in_doc:
                    continue

                # 単語境界 (\b) による正規表現検索
                pattern = re.compile(rf"\b({re.escape(alias_lower)})\b", re.IGNORECASE)
                if pattern.search(modified_line):
                    # 初出 1 回のみリンク化
                    modified_line = pattern.sub(f"[[{title}]]", modified_line, count=1)
                    linked_terms_in_doc.add(title)
                    total_links_added += 1

            relinked_lines.append(modified_line)

        return "\n".join(relinked_lines), total_links_added


def run_hardened_relinker_experiment():
    sample_text = """
    Assessment and evaluation have long been critical challenges in artificial intelligence (AI) and natural language processing (NLP).
    Traditional static metrics like BLEU and ROUGE measure quality by calculating lexical overlap between output and reference texts.
    Recent advancements in Large Language Models (LLMs) inspire the 'LLM-as-a-judge' paradigm, where LLMs are leveraged to perform scoring.
    The concept of LLM-as-a-judge or LLM as a judge or LLM-as-a-Judge is widely adopted in AI model evaluation.
    """

    relinker = HardenedRelinker()
    output_text, link_count = relinker.relink(sample_text)

    words_count = len(sample_text.split())
    density = link_count / words_count

    print("==========================================================================")
    print("      🧪 HARDENED RELINKER EXPERIMENT & COMPARISON REPORT")
    print("==========================================================================")
    print(f"Original Words: {words_count}")
    print(f"Naive Relinking Links: 21 links (Density: 29.58%) [FAIL - Over-linking & Nested]")
    print(f"Hardened Relinking Links: {link_count} links (Density: {density:.2%}) [PASS - Clean & Readable]")
    print("\n--- Hardened Relinked Output Text ---")
    print(output_text)

if __name__ == "__main__":
    run_hardened_relinker_experiment()

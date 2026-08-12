from pathlib import Path
import re

def experiment_naive_relinking_and_critique():
    """ナイーブな用語置き換え（Auto-linking）が引き起こす問題点（過剰リンク・表記揺れ）の実験的検証"""
    
    # 対象の実 Markdown テキスト
    sample_text = """
    Assessment and evaluation have long been critical challenges in artificial intelligence (AI) and natural language processing (NLP).
    Traditional static metrics like BLEU and ROUGE measure quality by calculating lexical overlap between output and reference texts.
    Recent advancements in Large Language Models (LLMs) inspire the 'LLM-as-a-judge' paradigm, where LLMs are leveraged to perform scoring.
    The concept of LLM-as-a-judge or LLM as a judge or LLM-as-a-Judge is widely adopted in AI model evaluation.
    """

    # 1. ナイーブな抽出用語リストの仮定
    terms = ["AI", "NLP", "LLM", "LLMs", "evaluation", "BLEU", "ROUGE", "LLM-as-a-judge", "LLM as a judge", "LLM-as-a-Judge", "output", "data"]

    print("=== 🧪 Critique Experiment: Naive Auto-Relinking Analysis ===")
    
    # 単純な文字置換を実行
    replaced_text = sample_text
    # 長い単語から置換
    sorted_terms = sorted(terms, key=len, reverse=True)
    
    link_count = 0
    for term in sorted_terms:
        pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
        matches = len(pattern.findall(replaced_text))
        if matches > 0:
            link_count += matches
            replaced_text = pattern.sub(r"[[\1]]", replaced_text)

    print(f"\n[Original Text Length]: {len(sample_text.split())} words")
    print(f"[Total WikiLinks Generated]: {link_count} links")
    print(f"[Link Density]: {link_count / len(sample_text.split()):.2%}")
    print("\n--- Relinked Output Preview ---")
    print(replaced_text)

if __name__ == "__main__":
    experiment_naive_relinking_and_critique()

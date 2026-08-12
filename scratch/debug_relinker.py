from wikid_steward.core.glossary import GlossaryTerm
from wikid_steward.core.relinker import WikiRelinker

terms = [
    GlossaryTerm(
        canonical_title="LLM-as-a-judge",
        slug="llm-as-a-judge",
        aliases=["LLM-as-a-judge", "LLM as a judge"],
        description="LLMを評価者とするアプローチ",
    ),
    GlossaryTerm(
        canonical_title="Language Model",
        slug="language-model",
        aliases=["Language Model", "LLM"],
        description="言語モデル",
    ),
]

text = "The LLM-as-a-judge method uses an LLM to score responses."
relinker = WikiRelinker(stop_words=set())
relinked_text, links_added = relinker.relink_text(text, terms)

print(f"Relinked Text: {relinked_text}")
print(f"Links Added: {links_added}")

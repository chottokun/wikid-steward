from wikid_steward.core.glossary import GlossaryTerm
from wikid_steward.core.relinker import WikiRelinker


def test_relinker_prevention_of_nested_brackets():
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

    # アサートチェック
    assert "[[LLM-as-a-judge]]" in relinked_text
    assert "[[Language Model]]" in relinked_text
    assert "[[[" not in relinked_text
    assert "]]]]" not in relinked_text
    assert links_added == 2


def test_relinker_respects_protected_blocks():
    terms = [
        GlossaryTerm(
            canonical_title="LLM-as-a-judge",
            slug="llm-as-a-judge",
            aliases=["LLM-as-a-judge"],
            description="評価モデル",
        ),
    ]

    text = "# LLM-as-a-judge Overview\nHere is an image: ![LLM-as-a-judge](assets/fig1.png) and an existing link [[LLM-as-a-judge]].\nAnd here is a plain mention of LLM-as-a-judge."

    relinker = WikiRelinker()
    relinked_text, links_added = relinker.relink_text(text, terms)

    lines = relinked_text.splitlines()
    # 見出し # は置換されない
    assert lines[0] == "# LLM-as-a-judge Overview"
    # 画像タグの alt は置換されない
    assert "![LLM-as-a-judge]" in lines[1]
    # 既存の [[LLM-as-a-judge]] はネストされない
    assert "[[[LLM-as-a-judge]]]" not in lines[1]
    # 平文の最後のみ [[LLM-as-a-judge]] 化される
    assert "[[LLM-as-a-judge]]" in lines[2]
    assert links_added == 1

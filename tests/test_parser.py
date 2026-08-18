from wikid_steward.core.parser import KnowledgeParser


def test_parser_initialization():
    parser = KnowledgeParser()
    assert parser is not None

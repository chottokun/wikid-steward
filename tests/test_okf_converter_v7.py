from wikid_steward.core.okf_converter import (
    ActorInfo,
    OKFDocumentData,
    SourceEntry,
    VerifiedEntry,
    generate_okf_v7_frontmatter,
    parse_okf_frontmatter,
)


def test_generate_and_parse_okf_v7_frontmatter():
    doc = OKFDocumentData(
        doc_type="Concept",
        title="ナレッジシステムの設計思想",
        description="コアコンセプトの解説",
        status="stable",
        stale_after="2027-08-14",
        generated=ActorInfo(by="wikid-steward/auto-compiler", at="2026-08-14T05:20:00Z"),
        verified=[VerifiedEntry(by="human:chottokun", at="2026-08-14T05:22:00Z")],
        sources=[
            SourceEntry(id="drawing-pdf", resource="/sources/drawing.pdf", title="技術図面 PDF")
        ],
        tags=["architecture", "wiki"],
    )

    yaml_frontmatter = generate_okf_v7_frontmatter(doc)
    assert "type: Concept" in yaml_frontmatter
    assert "title: ナレッジシステムの設計思想" in yaml_frontmatter
    assert "status: stable" in yaml_frontmatter
    assert "wikid-steward/auto-compiler" in yaml_frontmatter
    assert "human:chottokun" in yaml_frontmatter
    assert "drawing-pdf" in yaml_frontmatter

    markdown_file = f"{yaml_frontmatter}\n# Title\n\nBody text."
    frontmatter_dict, body = parse_okf_frontmatter(markdown_file)

    assert frontmatter_dict["type"] == "Concept"
    assert frontmatter_dict["title"] == "ナレッジシステムの設計思想"
    assert frontmatter_dict["status"] == "stable"
    assert frontmatter_dict["generated"]["by"] == "wikid-steward/auto-compiler"
    assert frontmatter_dict["verified"][0]["by"] == "human:chottokun"
    assert frontmatter_dict["sources"][0]["id"] == "drawing-pdf"
    assert "Body text." in body


def test_parse_frontmatter_without_yaml():
    markdown = "# Just title\n\nJust body"
    fm, body = parse_okf_frontmatter(markdown)
    assert fm == {}
    assert body == markdown

import pytest
from wikid_steward.core.okf_converter import (
    generate_okf_frontmatter,
    replace_image_links,
)


def test_generate_okf_frontmatter():
    frontmatter = generate_okf_frontmatter(
        doc_id="project-a_dwg-1",
        title="DWG Specification",
        doc_type="Technical Specification",
        source_path="raw_sources/project-a/DWG-1.pdf",
        profile_used="drawing",
        profile_source="directory_policy",
    )
    assert "id: project-a_dwg-1" in frontmatter
    assert "title: DWG Specification" in frontmatter
    assert "type: Technical Specification" in frontmatter
    assert "status: unreviewed" in frontmatter
    assert "source: raw_sources/project-a/DWG-1.pdf" in frontmatter
    assert "profile_used: drawing" in frontmatter
    assert "profile_source: directory_policy" in frontmatter




def test_replace_image_links():
    markdown = "Here is a picture: ![](file:///tmp/docling/fig1.png) and another ![](fig2.png)."
    slug = "project-a_dwg-1"
    result = replace_image_links(markdown, slug)

    assert "![fig1.png](assets/project-a_dwg-1/fig1.png)" in result
    assert "![fig2.png](assets/project-a_dwg-1/fig2.png)" in result

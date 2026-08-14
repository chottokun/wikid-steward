from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any
import yaml


@dataclass
class ActorInfo:
    by: str
    at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )


@dataclass
class VerifiedEntry:
    by: str  # 例: "human:chottokun"
    at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )


@dataclass
class SourceEntry:
    id: str  # 例: "drawing-pdf"
    resource: str  # 例: "/sources/drawing.pdf"
    title: str = ""  # 例: "技術図面 PDF"


@dataclass
class OKFDocumentData:
    doc_type: str = "Concept"  # REQUIRED (Concept, Runbook, Article, Source など)
    title: str = ""
    description: str = ""
    status: str = "draft"  # draft | stable | deprecated
    stale_after: str | None = None  # YYYY-MM-DD
    generated: ActorInfo | None = None
    verified: list[VerifiedEntry] = field(default_factory=list)
    sources: list[SourceEntry] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    custom_metadata: dict[str, Any] = field(default_factory=dict)


def generate_okf_v7_frontmatter(doc: OKFDocumentData) -> str:
    """OKF v0.2 (v7.0) に適合する YAML Frontmatter を生成する。"""
    data: dict[str, Any] = {
        "type": doc.doc_type,
    }
    if doc.title:
        data["title"] = doc.title
    if doc.description:
        data["description"] = doc.description

    data["status"] = doc.status

    if doc.stale_after:
        data["stale_after"] = doc.stale_after

    if doc.generated:
        data["generated"] = {"by": doc.generated.by, "at": doc.generated.at}

    if doc.verified:
        data["verified"] = [{"by": v.by, "at": v.at} for v in doc.verified]

    if doc.sources:
        data["sources"] = [
            {"id": s.id, "resource": s.resource, "title": s.title}
            for s in doc.sources
        ]

    if doc.tags:
        data["tags"] = doc.tags

    if doc.custom_metadata:
        for k, v in doc.custom_metadata.items():
            data[k] = v

    yaml_str = yaml.dump(data, allow_unicode=True, sort_keys=False)
    return f"---\n{yaml_str}---\n"


def parse_okf_frontmatter(content_or_path: str | Path) -> tuple[dict[str, Any], str]:
    """Markdown テキストまたはファイルから YAML フロントマターと本文を分離して返す。

    Returns:
        (frontmatter_dict, body_markdown)
    """
    text = ""
    if isinstance(content_or_path, Path):
        text = content_or_path.read_text(encoding="utf-8")
    else:
        # 文字列がファイルパスとして存在する場合はファイルを読み、そうでなければテキストとみなす
        try:
            p = Path(content_or_path)
            if p.exists() and p.is_file():
                text = p.read_text(encoding="utf-8")
            else:
                text = content_or_path
        except Exception:
            text = content_or_path

    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    yaml_raw = parts[1]
    body = parts[2].lstrip("\r\n")

    try:
        data = yaml.safe_load(yaml_raw) or {}
        if isinstance(data, dict):
            return data, body
        return {}, body
    except Exception:
        return {}, body


def generate_okf_frontmatter(
    doc_id: str,
    title: str,
    doc_type: str,
    source_path: str,
    tags: list[str] | None = None,
    profile_used: str = "paper",
    profile_source: str = "default",
    custom_metadata: dict | None = None,
) -> str:
    """旧バージョン互換用 OKF フロントマター生成関数"""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    doc = OKFDocumentData(
        doc_type=doc_type,
        title=title,
        status="draft",
        generated=ActorInfo(by=f"wikid-steward/{profile_used}", at=now_iso),
        sources=[SourceEntry(id="source", resource=source_path, title=title)],
        tags=tags or ["raw_ingest"],
        custom_metadata=custom_metadata or {},
    )
    return generate_okf_v7_frontmatter(doc)


def replace_image_links(
    markdown_content: str,
    slug: str,
    extracted_image_names: list[str] | None = None,
) -> str:
    """Markdown 内の画像リンクを Obsidian 互換の 'assets/{slug}/{画像名}' 相対リンクに置換し、

    本文中に埋め込みが無い場合は抽出された画像アセットリンクを本文に埋め込む。
    """
    def _replace_match(match: re.Match) -> str:
        alt_text = match.group(1) or "Image"
        img_path = match.group(2) or ""
        img_name = img_path.split("/")[-1].split("\\")[-1]
        return f"![{img_name}](assets/{slug}/{img_name})"

    pattern_md = r"\!\[(.*?)\]\((.*?)\)"
    pattern_wiki = r"\!\[\[(.*?)\]\]"

    replaced_md = re.sub(pattern_md, _replace_match, markdown_content)

    def _replace_wiki(match: re.Match) -> str:
        img_path = match.group(1) or ""
        img_name = img_path.split("/")[-1].split("\\")[-1]
        return f"![{img_name}](assets/{slug}/{img_name})"

    replaced_md = re.sub(pattern_wiki, _replace_wiki, replaced_md)

    if extracted_image_names:
        missing_images = []
        for img_name in extracted_image_names:
            if f"assets/{slug}/{img_name}" not in replaced_md:
                missing_images.append(img_name)

        if missing_images:
            image_embed_blocks = []
            for img_name in missing_images:
                embed_code = (
                    f"\n\n![{img_name}](assets/{slug}/{img_name})\n"
                    f"> [!info] 📷 抽出図表アセット ({img_name})\n"
                )
                image_embed_blocks.append(embed_code)

            replaced_md += "\n\n## 📊 抽出図表・画像アセット\n" + "".join(image_embed_blocks)

    return replaced_md

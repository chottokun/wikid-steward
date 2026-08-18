from datetime import datetime, timezone
from pathlib import Path

from wikid_steward.core.okf_converter import (
    ActorInfo,
    OKFDocumentData,
    SourceEntry,
    VerifiedEntry,
    generate_okf_v7_frontmatter,
    parse_okf_frontmatter,
)


def review_file(
    file_path: Path | str,
    reviewer: str = "human:unknown",
    wiki_dir: Path | str | None = None,
    target_dir_name: str = "concepts",
) -> Path:
    """指定されたファイルを人間が査読した記録 (verified) を追記し、status を stable に昇格させる。

    ファイルが stubs/ 配下にある場合は、自動的に本番ディレクトリ（concepts/ 等）に移動する。
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    content = path.read_text(encoding="utf-8")
    meta, body = parse_okf_frontmatter(content)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # verified リストの更新
    verified_list = meta.get("verified") or []
    new_verified: list[VerifiedEntry] = []
    if isinstance(verified_list, list):
        for v in verified_list:
            if isinstance(v, dict) and "by" in v:
                new_verified.append(VerifiedEntry(by=v["by"], at=v.get("at", now_iso)))

    new_verified.append(VerifiedEntry(by=reviewer, at=now_iso))

    sources_list = meta.get("sources") or []
    new_sources: list[SourceEntry] = []
    if isinstance(sources_list, list):
        for s in sources_list:
            if isinstance(s, dict) and "id" in s:
                new_sources.append(
                    SourceEntry(
                        id=str(s["id"]),
                        resource=str(s.get("resource", "")),
                        title=str(s.get("title", "")),
                    )
                )

    generated_info = None
    if "generated" in meta and isinstance(meta["generated"], dict):
        g = meta["generated"]
        generated_info = ActorInfo(
            by=g.get("by", "unknown"),
            at=g.get("at", now_iso),
        )

    # 昇格ドキュメントデータの作成
    doc = OKFDocumentData(
        doc_type=meta.get("type", "Concept"),
        title=meta.get("title", path.stem),
        description=meta.get("description", ""),
        status="stable",  # stable に昇格
        stale_after=meta.get("stale_after"),
        generated=generated_info,
        verified=new_verified,
        sources=new_sources,
        tags=meta.get("tags") or [],
        custom_metadata={
            k: v
            for k, v in meta.items()
            if k
            not in (
                "type",
                "title",
                "description",
                "status",
                "stale_after",
                "generated",
                "verified",
                "sources",
                "tags",
            )
        },
    )

    new_frontmatter = generate_okf_v7_frontmatter(doc)
    new_full_content = f"{new_frontmatter}\n{body.lstrip()}"

    # 昇格ルーティング（stubs/ 配下の場合）
    is_in_stubs = "stubs" in path.parts

    if is_in_stubs:
        base_wiki = Path(wiki_dir) if wiki_dir else path.parent.parent
        target_dir = base_wiki / target_dir_name
        target_dir.mkdir(parents=True, exist_ok=True)
        new_path = target_dir / path.name

        new_path.write_text(new_full_content, encoding="utf-8")
        path.unlink()
        return new_path
    else:
        path.write_text(new_full_content, encoding="utf-8")
        return path

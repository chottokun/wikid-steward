from pathlib import Path
from wikid_steward.core.okf_converter import generate_okf_frontmatter


def generate_moc_for_directory(dir_path: Path, base_wiki_dir: Path) -> Path:
    """指定されたディレクトリ配下のドキュメント情報を解析し、

    動的 MOC (index.md) を自動生成・更新する。
    """
    category_name = dir_path.relative_to(base_wiki_dir).as_posix()
    if category_name == ".":
        category_name = "Root Vault"

    md_files = [
        f for f in dir_path.glob("*.md") if f.name != "index.md" and not f.name.endswith(".bak")
    ]

    doc_entries = []
    for f in md_files:
        content = f.read_text(encoding="utf-8")
        title = f.stem
        doc_type = "Document"

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                meta = yaml.safe_load(parts[1]) or {}
                title = str(meta.get("title", title))
                doc_type = str(meta.get("type", doc_type))

        doc_entries.append((str(title), str(doc_type), f.name))

    doc_entries.sort(key=lambda x: x[0])

    frontmatter = generate_okf_frontmatter(
        doc_id=f"moc_{dir_path.name}",
        title=f"Map of Content: {category_name}",
        doc_type="Map of Content",
        source_path=f"wiki/{category_name}",
    )

    body = [
        f"# 🗺️ Map of Content: {category_name}\n",
        f"全 {len(doc_entries)} 件のドキュメントが登録されています。\n",
        "## 📑 ドキュメント目次\n",
    ]

    for title, doc_type, filename in doc_entries:
        body.append(f"- [{title}]({filename}) `[{doc_type}]`")

    index_path = dir_path / "index.md"
    index_content = f"{frontmatter}\n" + "\n".join(body) + "\n"
    index_path.write_text(index_content, encoding="utf-8")
    return index_path


def generate_all_mocs(wiki_dir: Path | str) -> list[Path]:
    """wiki/ 配下のすべてのサブカテゴリに対し MOC (index.md) を一括自動生成する"""
    base_wiki = Path(wiki_dir)
    if not base_wiki.exists():
        return []

    generated_mocs = []
    subdirs = [d for d in base_wiki.glob("**") if d.is_dir()]

    for d in subdirs:
        # assets フォルダなどは除外
        if "assets" in d.parts:
            continue
        moc_path = generate_moc_for_directory(d, base_wiki)
        generated_mocs.append(moc_path)

    return generated_mocs

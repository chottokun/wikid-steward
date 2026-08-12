from datetime import datetime, timezone
import re
import yaml


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
    """Google OKF v0.2 に適合する【層A】YAML Frontmatter を生成する。

    Args:
        doc_id: グローバル一意な Slug名
        title: ドキュメントタイトル
        doc_type: OKFドキュメント種別 (例: "Technical Specification")
        source_path: 一次ソース原本への相対パス
        tags: タグのリスト
        profile_used: 適用されたパースプロファイル名 ("paper", "drawing" 等)
        profile_source: 判定理由 ("sidecar_yaml", "directory_policy", "default")
        custom_metadata: ユーザー定義追加メタデータ

    Returns:
        YAML Frontmatter 文字列 ("---\n...---\n")
    """
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    provenance_data = {
        "extracted": 0.90,
        "inferred": 0.10,
        "inferred_by": "wikid-steward v0.1",
        "profile_used": profile_used,
        "profile_source": profile_source,
    }

    data = {
        "id": doc_id,
        "title": title,
        "type": doc_type,
        "source": source_path,
        "provenance": provenance_data,
        "status": "unreviewed",
        "created": now_iso,
        "tags": tags or ["raw_ingest"],
    }

    if custom_metadata:
        data["custom_metadata"] = custom_metadata

    yaml_str = yaml.dump(data, allow_unicode=True, sort_keys=False)
    return f"---\n{yaml_str}---\n"


def replace_image_links(
    markdown_content: str,
    slug: str,
    extracted_image_names: list[str] | None = None,
) -> str:
    """Markdown 内の画像リンクを Obsidian 互換の 'assets/{slug}/{画像名}' 相対リンクに置換し、

    本文中に埋め込みが無い場合は抽出された画像アセットリンクを本文に埋め込む。

    Args:
        markdown_content: doclingから抽出されたMarkdown本文
        slug: ファイルのスラッグ名
        extracted_image_names: 抽出された画像ファイル名のリスト (例: ['fig1.png', 'fig2.png'])

    Returns:
        画像リンクが埋め込まれたMarkdown本文
    """

    def _replace_match(match: re.Match) -> str:
        alt_text = match.group(1) or "Image"
        img_path = match.group(2) or ""
        img_name = img_path.split("/")[-1].split("\\")[-1]
        # 決定論的 slug 名を絶対維持した相対パスを構築
        return f"![{img_name}](assets/{slug}/{img_name})"

    # 1. 標準の Markdown 画像記法 ![alt](path) および Obsidian 記法 ![[path]] の検索・置換
    pattern_md = r"\!\[(.*?)\]\((.*?)\)"
    pattern_wiki = r"\!\[\[(.*?)\]\]"

    replaced_md = re.sub(pattern_md, _replace_match, markdown_content)

    def _replace_wiki(match: re.Match) -> str:
        img_path = match.group(1) or ""
        img_name = img_path.split("/")[-1].split("\\")[-1]
        return f"![{img_name}](assets/{slug}/{img_name})"

    replaced_md = re.sub(pattern_wiki, _replace_wiki, replaced_md)

    # 2. 本文中に画像リンクが含まれず、抽出された画像アセットが存在する場合の自動埋め込み
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

            # 本文末尾（または参照位置）に画像リンクブロックを自動統合
            replaced_md += "\n\n## 📊 抽出図表・画像アセット\n" + "".join(image_embed_blocks)

    return replaced_md

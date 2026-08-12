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


def replace_image_links(markdown_content: str, slug: str) -> str:
    """Markdown 内の画像リンクを Obsidian 互換の 'assets/{slug}/{画像名}.png' 相対リンクに置換する。

    Args:
        markdown_content: doclingから抽出されたMarkdown本文
        slug: ファイルのスラッグ名

    Returns:
        置換済みのMarkdown本文
    """

    def _replace_match(match: re.Match) -> str:
        alt_text = match.group(1) or ""
        img_path = match.group(2) or ""

        # 画像ファイル名の抽出 (例: /tmp/docling/fig1.png -> fig1.png)
        img_name = img_path.split("/")[-1].split("\\")[-1]

        # 唯一ルール: assets/{slug}/{img_name}
        return f"![[assets/{slug}/{img_name}]]"

    # Markdown 標準画像記法 ! [alt] (path) の検索パターン
    pattern = r"\!\[(.*?)\]\((.*?)\)"
    replaced_md = re.sub(pattern, _replace_match, markdown_content)

    return replaced_md

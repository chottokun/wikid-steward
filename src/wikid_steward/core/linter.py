import difflib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from wikid_steward.core.human_memo import HUMAN_MEMO_TEMPLATE
from wikid_steward.core.okf_converter import (
    ActorInfo,
    OKFDocumentData,
    generate_okf_v7_frontmatter,
    parse_okf_frontmatter,
)
from wikid_steward.core.slug import generate_slug


def calculate_string_similarity(s1: str, s2: str) -> float:
    """ひらがな・カタカナ正規化と Levenshtein / SequenceMatcher を併用した高精度類似度計算"""

    def _normalize(s: str) -> str:
        # ひらがな (U+3041〜U+3096) を カタカナ (U+30A1〜U+30F6) に変換 (差分: +0x60)
        return "".join(
            chr(ord(c) + 0x60) if "\u3041" <= c <= "\u3096" else c for c in s.lower().strip()
        )

    n1, n2 = _normalize(s1), _normalize(s2)
    if n1 == n2:
        return 1.0

    ratio_seq = difflib.SequenceMatcher(None, n1, n2).ratio()

    len1, len2 = len(n1), len(n2)
    if max(len1, len2) == 0:
        return 1.0

    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if n1[i - 1] == n2[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    dist = dp[len1][len2]
    max_len = max(len1, len2)
    ratio_lev = (max_len - dist) / max_len

    return max(ratio_seq, ratio_lev)


@dataclass
class LintIssue:
    file_path: str
    issue_type: str  # "BROKEN_IMAGE_LINK", "MISSING_FRONTMATTER", "ORPHAN_NOTE", "ORPHAN_FOOTNOTE", "TYPO_SUGGESTION", "BROKEN_WIKILINK"
    message: str


@dataclass
class LintReport:
    total_files: int
    issues: list[LintIssue]
    is_healthy: bool
    stubs_created: list[str]


class KnowledgeLinter:
    """wiki/ 配下のナレッジベース全体の健全性（リンク切れ、スタブ起票、タイポ警告、脚注整合性、画像パス）を

    一括検証・自己修復するセルフヒーリングリントモジュール (v7.0)。
    """

    def __init__(self, wiki_dir: Path | str, stubs_dir_name: str = "stubs"):
        self.wiki_dir = Path(wiki_dir)
        self.stubs_dir = self.wiki_dir / stubs_dir_name

    def run_lint(self, auto_create_stubs: bool = True) -> LintReport:
        if not self.wiki_dir.exists():
            return LintReport(total_files=0, issues=[], is_healthy=True, stubs_created=[])

        md_files = list(self.wiki_dir.glob("**/*.md"))
        issues: list[LintIssue] = []
        stubs_created: list[str] = []

        # 1. 既存の全ノートタイトル・Slug マップを収集
        title_to_file: dict[str, Path] = {}
        slug_to_file: dict[str, Path] = {}
        all_titles: list[str] = []

        for md_file in md_files:
            meta, body = parse_okf_frontmatter(md_file)
            title = meta.get("title") or md_file.stem
            slug = md_file.stem
            title_to_file[title.strip()] = md_file
            slug_to_file[slug] = md_file
            all_titles.append(title.strip())

        # 2. 全ファイルのリンク・画像・フロントマター・脚注を走査
        wikilink_pattern = re.compile(r"\[\[([^\]\r\n]+)\]\]")
        image_pattern = re.compile(r"\!\[.*?\]\((.*?)\)")
        footnote_pattern = re.compile(r"\[\^([a-zA-Z0-9_-]+)\]")

        referenced_files: set[str] = set()
        missing_wikilinks: dict[str, list[str]] = {}  # term -> [referencing_files]

        for md_file in md_files:
            rel_file = md_file.relative_to(self.wiki_dir).as_posix()
            meta, body = parse_okf_frontmatter(md_file)
            content = md_file.read_text(encoding="utf-8")

            # Frontmatter チェック
            if not content.startswith("---") or not meta:
                issues.append(
                    LintIssue(
                        file_path=rel_file,
                        issue_type="MISSING_FRONTMATTER",
                        message="有効な YAML Frontmatter が見つかりません。",
                    )
                )
            else:
                if "type" not in meta:
                    issues.append(
                        LintIssue(
                            file_path=rel_file,
                            issue_type="MISSING_FRONTMATTER",
                            message="必須 Frontmatter キー 'type' が欠落しています。",
                        )
                    )

            # 画像リンクチェック
            for img_link in image_pattern.findall(content):
                img_clean = img_link.strip()
                if img_clean.startswith(("http://", "https://", "data:")):
                    continue
                if img_clean.startswith("file://"):
                    img_clean = img_clean.replace("file://", "")

                img_path = (md_file.parent / img_clean).resolve()
                if not img_path.exists() or not img_path.is_file():
                    issues.append(
                        LintIssue(
                            file_path=rel_file,
                            issue_type="BROKEN_IMAGE_LINK",
                            message=f"画像ファイルが存在しません: {img_link}",
                        )
                    )

            # 脚注 (Footnotes) と Frontmatter sources の整合性スキャン
            sources_ids = set()
            if "sources" in meta and isinstance(meta["sources"], list):
                for s in meta["sources"]:
                    if isinstance(s, dict) and "id" in s:
                        sources_ids.add(str(s["id"]))

            for footnote_id in footnote_pattern.findall(content):
                if footnote_id not in sources_ids:
                    issues.append(
                        LintIssue(
                            file_path=rel_file,
                            issue_type="ORPHAN_FOOTNOTE",
                            message=f"脚注 [^{footnote_id}] の定義が Frontmatter sources に存在しません。",
                        )
                    )

            # WikiLink の収集と未定義リンクの検知
            for link_match in wikilink_pattern.findall(content):
                term = link_match.split("|", 1)[0].strip()
                # 既存ノートにタイトルまたはSlugが存在するか
                slug_cand = generate_slug(term)
                if term in title_to_file or slug_cand in slug_to_file or term in slug_to_file:
                    target_file = (
                        title_to_file.get(term)
                        or slug_to_file.get(slug_cand)
                        or slug_to_file.get(term)
                    )
                    if target_file:
                        referenced_files.add(target_file.relative_to(self.wiki_dir).as_posix())
                else:
                    if term not in missing_wikilinks:
                        missing_wikilinks[term] = []
                    missing_wikilinks[term].append(rel_file)

        # 3. 未定義 WikiLink に対するタイポサジェストとスタブ起票
        for missing_term, referrers in missing_wikilinks.items():
            # タイポあいまいマッチング (類似度 >= 0.75 の候補を検索)
            typo_candidates = []
            for exist_title in all_titles:
                ratio = calculate_string_similarity(missing_term, exist_title)
                if ratio >= 0.75 and missing_term.lower() != exist_title.lower():
                    typo_candidates.append(exist_title)

            if typo_candidates:
                cand_str = ", ".join([f"[[{c}]]" for c in typo_candidates])
                for ref in referrers:
                    issues.append(
                        LintIssue(
                            file_path=ref,
                            issue_type="TYPO_SUGGESTION",
                            message=f"リンク切れ [[{missing_term}]] は既存の {cand_str} のタイポの可能性があります (警告のみ)。",
                        )
                    )

            # スタブ自動起票 (wiki/stubs/{slug}.md)
            if auto_create_stubs:
                stub_slug = generate_slug(missing_term)
                stub_file = self.stubs_dir / f"{stub_slug}.md"
                if not stub_file.exists():
                    self.stubs_dir.mkdir(parents=True, exist_ok=True)
                    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                    stub_doc = OKFDocumentData(
                        doc_type="Concept",
                        title=missing_term,
                        description=f"[[{missing_term}]] の自動起票スタブ",
                        status="draft",
                        generated=ActorInfo(by="wikid-steward/linter", at=now_iso),
                        tags=["stub", "auto_generated"],
                    )
                    frontmatter_text = generate_okf_v7_frontmatter(stub_doc)

                    stub_body = (
                        f"# {missing_term}\n\n"
                        f"※ 本ページは [[wikid-steward]] のセルフヒーリング機能によって自動起票されたスタブ（下書き）です。"
                        f"他のノートでの使われ方（バックリンク文脈）を元に自動で定義レジュメが逆合成されるか、手動で加筆されるのを待っています。\n\n"
                        f"{HUMAN_MEMO_TEMPLATE}"
                    )

                    stub_file.write_text(f"{frontmatter_text}\n{stub_body}", encoding="utf-8")
                    stubs_created.append(stub_slug)

        return LintReport(
            total_files=len(md_files),
            issues=issues,
            is_healthy=len([i for i in issues if i.issue_type not in ("TYPO_SUGGESTION",)]) == 0,
            stubs_created=stubs_created,
        )

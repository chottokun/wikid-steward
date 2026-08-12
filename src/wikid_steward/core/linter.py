import re
from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class LintIssue:
    file_path: str
    issue_type: str  # "BROKEN_IMAGE_LINK", "MISSING_FRONTMATTER", "ORPHAN_NOTE"
    message: str


@dataclass
class LintReport:
    total_files: int
    issues: list[LintIssue]
    is_healthy: bool


class KnowledgeLinter:
    """wiki/ 配下のナレッジベース全体の健全性（画像リンク切れ・Frontmatter欠損・孤立ノート）を

    一括検証・リポートするセルフヒーリングリントモジュール。
    """

    def __init__(self, wiki_dir: Path | str):
        self.wiki_dir = Path(wiki_dir)

    def run_lint(self) -> LintReport:
        if not self.wiki_dir.exists():
            return LintReport(total_files=0, issues=[], is_healthy=True)

        md_files = list(self.wiki_dir.glob("**/*.md"))
        issues: list[LintIssue] = []

        all_rel_files = {f.relative_to(self.wiki_dir).as_posix() for f in md_files}
        referenced_files = set()

        for md_file in md_files:
            rel_file = md_file.relative_to(self.wiki_dir).as_posix()
            content = md_file.read_text(encoding="utf-8")

            # 1. OKF Frontmatter チェック
            if not content.startswith("---"):
                issues.append(
                    LintIssue(
                        file_path=rel_file,
                        issue_type="MISSING_FRONTMATTER",
                        message="YAML Frontmatter (---) が見つかりません。",
                    )
                )
            else:
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    try:
                        meta = yaml.safe_load(parts[1]) or {}
                        for req_key in ["id", "title"]:
                            if req_key not in meta:
                                issues.append(
                                    LintIssue(
                                        file_path=rel_file,
                                        issue_type="MISSING_FRONTMATTER",
                                        message=f"必須 Frontmatter キー '{req_key}' が欠落しています。",
                                    )
                                )
                    except Exception as e:
                        issues.append(
                            LintIssue(
                                file_path=rel_file,
                                issue_type="MISSING_FRONTMATTER",
                                message=f"YAML の解析に失敗しました: {e}",
                            )
                        )

            # 2. 画像パスリンク切れチェック ![alt](assets/...)
            image_matches = re.findall(r"\!\[.*?\]\((.*?)\)", content)
            for img_link in image_matches:
                img_link_clean = img_link.strip()
                # 外部 Web URL や file:// スキップ
                if img_link_clean.startswith(("http://", "https://", "data:")):
                    continue
                if img_link_clean.startswith("file://"):
                    img_link_clean = img_link_clean.replace("file://", "")

                img_path = (md_file.parent / img_link_clean).resolve()
                if not img_path.exists() or not img_path.is_file():
                    issues.append(
                        LintIssue(
                            file_path=rel_file,
                            issue_type="BROKEN_IMAGE_LINK",
                            message=f"画像ファイルが存在しません: {img_link}",
                        )
                    )

            # 3. 参照リンク収集 ([label](filename.md) または [[term]])
            link_matches = re.findall(r"\[.*?\]\(((?!http).*?)\)", content)
            for link in link_matches:
                target_rel = (md_file.parent / link).resolve()
                if target_rel.exists() and target_rel.is_relative_to(self.wiki_dir):
                    referenced_files.add(
                        target_rel.relative_to(self.wiki_dir).as_posix()
                    )

        # 4. 孤立ノート (Orphan Notes) 検知 (index.md 以外でどこからもリンクされていない)
        for rel_file in all_rel_files:
            if not rel_file.endswith("index.md") and rel_file not in referenced_files:
                # glossary 配下のノートは自動用語参照されるため考慮
                if not rel_file.startswith("glossary/"):
                    issues.append(
                        LintIssue(
                            file_path=rel_file,
                            issue_type="ORPHAN_NOTE",
                            message="他のノートからリンクされていない孤立ノートです。",
                        )
                    )

        return LintReport(
            total_files=len(md_files),
            issues=issues,
            is_healthy=len(issues) == 0,
        )

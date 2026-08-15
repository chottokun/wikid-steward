from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any
import yaml

from wikid_steward.core.human_memo import merge_human_memo
from wikid_steward.core.llm_client import OpenAICompatibleLLMClient
from wikid_steward.core.okf_converter import (
    ActorInfo,
    OKFDocumentData,
    generate_okf_v7_frontmatter,
    parse_okf_frontmatter,
)
from wikid_steward.core.slug import generate_slug


def is_trusted_context_source(frontmatter: dict[str, Any]) -> bool:
    """逆合成コンテキストとして採用可能な信頼性の高いソースか判定する（AI循環汚染防止フィルター）。

    採用条件:
    1. verified に人間による査読 (human:...) が含まれている
    2. または generated.by が人間 (human:...)
    3. または status == "stable" (人間により安定版に昇格済み)

    除外条件:
    - status == "draft" かつ AI生成物で人間査読がないもの
    """
    if not frontmatter:
        return False

    # 1. verified に human: が存在するか
    verified_list = frontmatter.get("verified") or []
    if isinstance(verified_list, list):
        for v in verified_list:
            if isinstance(v, dict) and "by" in v and str(v["by"]).startswith("human:"):
                return True

    # 2. generated.by が human: で始まるか
    generated = frontmatter.get("generated") or {}
    if isinstance(generated, dict):
        by_actor = str(generated.get("by", ""))
        if by_actor.startswith("human:"):
            return True

    # 3. status が stable か
    status = str(frontmatter.get("status", "")).lower()
    if status == "stable":
        return True

    # それ以外の draft かつ AI 生成物は循環汚染源として 100% 除外
    return False


@dataclass
class BacklinkContext:
    source_file: Path
    source_title: str
    context_snippet: str
    frontmatter: dict[str, Any]


class BacklinkCollector:
    """wiki/ ディレクトリ全体の被リンクを有向グラフとして集約し、重複排除と文脈抽出を行う"""

    def __init__(self, wiki_dir: Path | str):
        self.wiki_dir = Path(wiki_dir)

    def find_backlinks(
        self, target_term: str, filter_untrusted: bool = True
    ) -> list[BacklinkContext]:
        """指定された用語に対するユニークなバックリンク文脈を収集する。

        同一ドキュメント内に複数回出現しても1ドキュメントにつき1件として重複排除する。
        """
        results: list[BacklinkContext] = []
        target_slug = generate_slug(target_term)
        wikilink_pattern = re.compile(r"\[\[([^\]\r\n]+)\]\]")

        for md_file in self.wiki_dir.glob("**/*.md"):
            # 自分自身（スタブ自身）や stubs/ 配下の別スタブは参照元から除外
            if "stubs" in md_file.parts:
                continue

            meta, body = parse_okf_frontmatter(md_file)
            if filter_untrusted and not is_trusted_context_source(meta):
                continue

            source_title = meta.get("title") or md_file.stem
            lines = body.splitlines()
            matching_snippets: list[str] = []

            for i, line in enumerate(lines):
                matches = wikilink_pattern.findall(line)
                hit = False
                for m in matches:
                    term = m.split("|", 1)[0].strip()
                    if term == target_term or generate_slug(term) == target_slug:
                        hit = True
                        break

                if hit:
                    # 前後1〜2行のコンテキストスニペットを抽出
                    start = max(0, i - 1)
                    end = min(len(lines), i + 2)
                    snippet = "\n".join(lines[start:end]).strip()
                    matching_snippets.append(snippet)

            if matching_snippets:
                # 1ファイルにつき代表スニペットを結合して1件の BacklinkContext を作成 (重複排除)
                combined_snippet = "\n---\n".join(matching_snippets[:3])
                results.append(
                    BacklinkContext(
                        source_file=md_file,
                        source_title=source_title,
                        context_snippet=combined_snippet,
                        frontmatter=meta,
                    )
                )

        return results


class RetroCompiler:
    """蓄積された信頼性の高いバックリンク文脈から、LLM を用いて用語定義レジュメを自動逆合成し、

    スタブから本番ディレクトリへ昇格させるモジュール (v7.0)。
    """

    def __init__(
        self,
        wiki_dir: Path | str,
        min_backlinks: int = 3,
        target_language: str = "Japanese",
        llm_client: Any | None = None,
        stubs_subdir: str = "stubs",
    ):
        self.wiki_dir = Path(wiki_dir)
        self.min_backlinks = min_backlinks
        self.target_language = target_language
        self.llm_client = llm_client or OpenAICompatibleLLMClient()
        self.stubs_dir = self.wiki_dir / stubs_subdir
        self.collector = BacklinkCollector(self.wiki_dir)

    def collect_backlinks_for_term(self, term: str) -> list[BacklinkContext]:
        return self.collector.find_backlinks(term, filter_untrusted=True)

    def compile_stub(
        self,
        term: str,
        target_dir_name: str = "concepts",
        force: bool = False,
    ) -> Path | None:
        """指定された用語のスタブに対し、十分なバックリンクが集まっている場合に定義を逆合成して昇格させる。

        Returns:
            昇格後のファイルパス（条件未達で実行されなかった場合は None）
        """
        stub_slug = generate_slug(term)
        target_stub_file: Path | None = None
        if self.stubs_dir.exists():
            for sf in self.stubs_dir.glob("*.md"):
                if sf.stem == stub_slug or sf.stem == term:
                    target_stub_file = sf
                    break
                meta, _ = parse_okf_frontmatter(sf)
                if meta.get("title") == term:
                    target_stub_file = sf
                    break

        if not target_stub_file or not target_stub_file.exists():
            return None

        stub_file = target_stub_file
        actual_slug = stub_file.stem

        backlinks = self.collect_backlinks_for_term(term)
        if not force and len(backlinks) < self.min_backlinks:
            return None

        # 既存スタブの手書きメモやメタデータを読み込む
        existing_content = stub_file.read_text(encoding="utf-8")
        existing_meta, _ = parse_okf_frontmatter(existing_content)

        # LLM 用プロンプトの構築
        contexts_text = []
        for i, b in enumerate(backlinks, 1):
            contexts_text.append(
                f"【引用元 {i}】ノート名: 《{b.source_title}》\n"
                f"文脈:\n{b.context_snippet}\n"
            )
        all_context = "\n".join(contexts_text)

        system_prompt = (
            f"あなたは組織固有のナレッジを体系化するエキスパートAIです。\n"
            f"複数のドキュメントで言及されている未定義用語『{term}』について、"
            f"提供された引用文脈からその意味・使われ方・重要ポイントを分析し、"
            f"組織固有の用語解説・定義レジュメを GFM Markdown 形式で作成してください。\n"
            f"必ず出力言語は {self.target_language} で統一してください。\n"
            f"出力には YAML Frontmatter や見出し1 (# {term}) を含めず、見出し2 (## 概要 等) から本文を開始してください。"
        )

        user_prompt = f"以下の信頼できる引用文脈に基づいて、『{term}』の解説を作成してください:\n\n{all_context}"

        generated_body = self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        new_doc = OKFDocumentData(
            doc_type="Concept",
            title=term,
            description=f"[[{term}]] の定義・解説レジュメ",
            status="stable",  # 自動逆合成完了で stable に昇格
            generated=ActorInfo(by="wikid-steward/auto-compiler", at=now_iso),
            tags=["concept", "auto_compiled"],
        )
        new_frontmatter = generate_okf_v7_frontmatter(new_doc)

        full_new_content = f"{new_frontmatter}\n# {term}\n\n{generated_body.strip()}\n"

        # 既存の手書きメモを安全にマージ（保護）
        merged_content = merge_human_memo(
            new_content=full_new_content, existing_content=existing_content
        )

        # 本番ディレクトリ (wiki/concepts/) への昇格保存
        target_dir = self.wiki_dir / target_dir_name
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"{actual_slug}.md"

        target_file.write_text(merged_content, encoding="utf-8")

        # 旧スタブファイルの削除（昇格移動の完了）
        if stub_file.exists():
            stub_file.unlink()

        return target_file

    def compile_all_ready_stubs(
        self, target_dir_name: str = "concepts"
    ) -> list[Path]:
        """バックリンク数が N 件以上に達しているすべてのスタブを逆合成して昇格させる"""
        if not self.stubs_dir.exists():
            return []

        promoted: list[Path] = []
        for stub_file in list(self.stubs_dir.glob("*.md")):
            meta, _ = parse_okf_frontmatter(stub_file)
            term = meta.get("title") or stub_file.stem
            promoted_file = self.compile_stub(term, target_dir_name=target_dir_name)
            if promoted_file:
                promoted.append(promoted_file)

        return promoted

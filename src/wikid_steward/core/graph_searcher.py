import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wikid_steward.core.config import get_config
from wikid_steward.core.llm_client import OpenAICompatibleLLMClient
from wikid_steward.core.okf_converter import parse_okf_frontmatter
from wikid_steward.core.slug import generate_slug


@dataclass
class SearchHit:
    file_path: str
    title: str
    score: float
    frontmatter: dict[str, Any]
    snippet: str


@dataclass
class SearchResult:
    query: str
    main_hits: list[dict[str, Any]]
    traversed_glossary_terms: list[dict[str, Any]]
    integrated_answer: str


class LightweightGraphSearchEngine:
    """外部ベクトルDB（Qdrant）に依存せず、OKF v0.2 構造化メタデータと

    1-Hop WikiLink グラフ巡回を純粋な Python で高速実行する軽量検索エンジン (v7.0)。
    """

    def __init__(self, llm_client: OpenAICompatibleLLMClient | None = None):
        self.llm_client = llm_client or OpenAICompatibleLLMClient()
        self.cfg = get_config()

    def search(
        self,
        query: str,
        wiki_dir: Path | str,
        top_k: int = 3,
        max_traversal_depth: int = 1,
    ) -> SearchResult:
        wiki_path = Path(wiki_dir)
        if not wiki_path.exists():
            return SearchResult(
                query=query,
                main_hits=[],
                traversed_glossary_terms=[],
                integrated_answer="wiki ディレクトリが存在しません。",
            )

        query_terms = [t.strip().lower() for t in query.split() if len(t.strip()) > 0]
        if not query_terms:
            return SearchResult(
                query=query,
                main_hits=[],
                traversed_glossary_terms=[],
                integrated_answer="クエリが空です。",
            )

        md_files = list(wiki_path.glob("**/*.md"))
        candidates: list[SearchHit] = []

        # 1. メタデータ＆全文スコアリング
        for md_file in md_files:
            meta, body = parse_okf_frontmatter(md_file)
            title = meta.get("title") or md_file.stem
            description = meta.get("description") or ""
            tags = meta.get("tags") or []
            if isinstance(tags, list):
                tags_str = " ".join([str(t) for t in tags])
            else:
                tags_str = str(tags)

            score = 0.0
            for term in query_terms:
                if term in title.lower():
                    score += 5.0
                if term in tags_str.lower():
                    score += 3.0
                if term in description.lower():
                    score += 2.0
                if term in body.lower():
                    score += 1.0

            if score > 0.0:
                rel_path = md_file.relative_to(wiki_path).as_posix()
                snippet = body.strip()[:300].replace("\n", " ")
                candidates.append(
                    SearchHit(
                        file_path=rel_path,
                        title=title,
                        score=score,
                        frontmatter=meta,
                        snippet=snippet,
                    )
                )

        # スコア順にソートして top_k を抽出
        candidates.sort(key=lambda x: x.score, reverse=True)
        top_hits = candidates[:top_k]

        main_hits_data = []
        wikilinks_found = set()
        wikilink_pattern = re.compile(r"\[\[([^\]\r\n]+)\]\]")

        for hit in top_hits:
            hit_file = wiki_path / hit.file_path
            content = hit_file.read_text(encoding="utf-8")
            for m in wikilink_pattern.findall(content):
                term = m.split("|", 1)[0].strip()
                if term and term != hit.title:
                    wikilinks_found.add(term)

            main_hits_data.append(
                {
                    "title": hit.title,
                    "file_path": hit.file_path,
                    "score": hit.score,
                    "snippet": hit.snippet,
                    "frontmatter": hit.frontmatter,
                }
            )

        # 2. 1-Hop グラフ巡回 (リンク先ノートの定義・要約を読み込み)
        traversed_terms = []
        max_hub = getattr(self.cfg.vector_db, "max_hub_degree", 25)
        # ハブノード爆発を防ぐため巡回リンク数を制限
        for term in list(wikilinks_found)[:max_hub]:
            term_slug = generate_slug(term)
            target_files = list(wiki_path.glob(f"**/{term_slug}.md"))
            if not target_files:
                target_files = list(wiki_path.glob(f"**/{term}.md"))

            if target_files:
                tf = target_files[0]
                t_meta, t_body = parse_okf_frontmatter(tf)
                t_title = t_meta.get("title") or term
                t_desc = t_meta.get("description") or t_body.strip()[:150].replace("\n", " ")
                traversed_terms.append(
                    {
                        "term": t_title,
                        "file": tf.relative_to(wiki_path).as_posix(),
                        "summary": t_desc,
                    }
                )

        # 3. LLM 統合要約プロンプト
        context_blocks = []
        for i, h in enumerate(main_hits_data, 1):
            context_blocks.append(
                f"【メイン情報 {i}】ノート名: {h['title']} ({h['file_path']})\n"
                f"内容要約: {h['snippet']}\n"
            )

        if traversed_terms:
            context_blocks.append("【関連用語定義 (1-Hop Traversal)】\n")
            for g in traversed_terms:
                context_blocks.append(f"・[[{g['term']}]] ({g['file']}): {g['summary']}\n")

        all_context = "\n".join(context_blocks)
        target_lang = getattr(self.cfg.llm, "target_language", "Japanese")

        system_prompt = (
            f"あなたは Wiki ナレッジグラフに精通したアシスタントです。\n"
            f"提供されたメインノートおよび巡回抽出された関連用語の文脈に基づいて、"
            f"ユーザーの質問『{query}』に対する簡潔で正確な統合回答を {target_lang} で作成してください。"
        )

        user_prompt = f"以下の知識コンテキストに基づいて回答してください:\n\n{all_context}"

        try:
            integrated_answer = self.llm_client.generate(
                prompt=user_prompt, system_prompt=system_prompt
            )
        except Exception as e:
            integrated_answer = f"回答生成中にエラーが発生しました: {e}"

        return SearchResult(
            query=query,
            main_hits=main_hits_data,
            traversed_glossary_terms=traversed_terms,
            integrated_answer=integrated_answer,
        )

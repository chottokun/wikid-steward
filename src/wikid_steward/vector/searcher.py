import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from wikid_steward.core.config import get_config
from wikid_steward.core.llm_client import OpenAICompatibleLLMClient
from wikid_steward.vector.indexer import QdrantKnowledgeIndexer


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


@runtime_checkable
class SearcherProtocol(Protocol):
    """Qdrant 検索エンジンおよび軽量ファイルベース検索エンジンの共通抽象インターフェース (Searcher Protocol)"""

    def search(
        self,
        query: str,
        wiki_dir: Path | str,
        top_k: int = 3,
        max_traversal_depth: int = 1,
    ) -> SearchResult: ...


class FallbackSearchEngine(SearcherProtocol):
    """Qdrant 検索エンジン (WikiGraphSearchEngine) の起動/クエリ処理が失敗した場合に

    自動的に LightweightGraphSearchEngine へフォールバックする安全策プロキシエンジン。
    """

    def __init__(
        self,
        primary_engine: SearcherProtocol | None = None,
        fallback_engine: SearcherProtocol | None = None,
    ):
        from wikid_steward.core.graph_searcher import LightweightGraphSearchEngine

        self.fallback_engine = fallback_engine or LightweightGraphSearchEngine()
        if primary_engine is not None:
            self.primary_engine = primary_engine
        else:
            try:
                self.primary_engine = WikiGraphSearchEngine()
            except Exception as e:
                print(
                    f"[FallbackSearchEngine] Failed to initialize Qdrant primary engine: {e}. Falling back to Lightweight engine."
                )
                self.primary_engine = None

    def search(
        self,
        query: str,
        wiki_dir: Path | str,
        top_k: int = 3,
        max_traversal_depth: int = 1,
    ) -> SearchResult:
        if self.primary_engine is not None:
            try:
                res = self.primary_engine.search(query, wiki_dir, top_k, max_traversal_depth)
                if res and res.main_hits:
                    return res
                print(
                    "[FallbackSearchEngine] Primary search returned empty hits or failed. Executing fallback engine..."
                )
            except Exception as e:
                print(
                    f"[FallbackSearchEngine] Primary search failed with error: {e}. Executing fallback engine..."
                )

        return self.fallback_engine.search(query, wiki_dir, top_k, max_traversal_depth)


def create_search_engine(
    backend: str = "auto",
    llm_client: OpenAICompatibleLLMClient | None = None,
) -> SearcherProtocol:
    """検索エンジンのファクトリ関数。backend: 'auto', 'qdrant', 'lightweight'"""
    from wikid_steward.core.graph_searcher import LightweightGraphSearchEngine

    if backend == "lightweight":
        return LightweightGraphSearchEngine(llm_client=llm_client)

    qdrant_engine = None
    try:
        qdrant_engine = WikiGraphSearchEngine(llm_client=llm_client)
    except Exception as e:
        print(f"[Search Engine Factory] Qdrant engine initialization failed: {e}")

    if backend == "qdrant":
        if qdrant_engine is not None:
            return qdrant_engine
        print(
            "[Search Engine Factory] Requested 'qdrant' backend, but it failed to initialize. Falling back to Lightweight engine."
        )
        return LightweightGraphSearchEngine(llm_client=llm_client)

    # backend == "auto"
    lightweight_engine = LightweightGraphSearchEngine(llm_client=llm_client)
    if qdrant_engine is None:
        return lightweight_engine
    return FallbackSearchEngine(primary_engine=qdrant_engine, fallback_engine=lightweight_engine)


class WikiGraphSearchEngine(SearcherProtocol):
    """LLM-Wiki の真骨頂である

    「Qdrant ベクトル検索 × WikiLink グラフ巡回 × LLM 統合回答」を具現化する検索エンジン。
    """

    def __init__(
        self,
        indexer: QdrantKnowledgeIndexer | None = None,
        llm_client: OpenAICompatibleLLMClient | None = None,
    ):
        self.indexer = indexer or QdrantKnowledgeIndexer(location=":memory:")
        self.llm_client = llm_client or OpenAICompatibleLLMClient()
        self.cfg = get_config()

    def search(
        self,
        query: str,
        wiki_dir: Path | str,
        top_k: int = 3,
        max_traversal_depth: int = 1,
    ) -> SearchResult:
        """クエリに対して Wiki グラフ拡張検索を実行し、統合回答と根拠ノードを返却する。"""
        wiki_path = Path(wiki_dir)

        # クエリのベクトル化と Qdrant 検索
        query_vectors = self.indexer.embed_texts([query])
        if not query_vectors:
            return SearchResult(
                query=query,
                main_hits=[],
                traversed_glossary_terms=[],
                integrated_answer="埋め込み生成に失敗しました。",
            )
        query_vector = query_vectors[0]

        try:
            q_res = self.indexer.client.query_points(
                collection_name=self.indexer.collection_name,
                query=query_vector,
                limit=top_k,
            )
            search_results = q_res.points
        except Exception as e:
            print(f"Qdrant query error: {e}")
            search_results = []

        main_hits = []
        wikilinks_found = set()

        alpha = 0.2  # PageRank ブースト重み係数
        for res in search_results:
            payload = res.payload or {}
            pr_score = float(payload.get("pagerank_score", 0.0))
            raw_sim = float(res.score)
            boosted_score = raw_sim + (alpha * pr_score)
            payload["score"] = boosted_score
            payload["raw_similarity"] = raw_sim
            payload["pagerank_score"] = pr_score
            main_hits.append(payload)

            # ヒットしたテキスト内の [[用語名]] を抽出
            content = payload.get("content", "")
            found = re.findall(r"\[\[(.*?)\]\]", content)
            for term in found:
                if len(term) >= 2:
                    wikilinks_found.add(term)

        # PageRank ブースト後のスコアで再ソート
        main_hits.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        # クエリ単体からの用語一致も補完
        for term_candidate in query.split():
            clean_candidate = re.sub(r"[^\w\-]", "", term_candidate)
            if len(clean_candidate) >= 2 and clean_candidate.upper() not in {
                "WHAT",
                "WITH",
                "THAT",
                "THIS",
                "FROM",
                "HAVE",
                "AND",
            }:
                wikilinks_found.add(clean_candidate)

        # 1-Hop グラフ巡回: 用語説明ノート (wiki/glossary/) を自動追跡
        glossary_hits = []
        glossary_dir = wiki_path / "glossary"

        max_hub_degree = self.cfg.vector_db.max_hub_degree
        max_traversal_tokens = self.cfg.vector_db.max_traversal_tokens
        accumulated_tokens = 0

        # 全 Markdown ファイルをロード（度数カウント用）
        all_md_texts = [f.read_text(encoding="utf-8") for f in wiki_path.glob("**/*.md")]

        for term in list(wikilinks_found)[:10]:
            # 度数 (Degree) の計算: 全 Vault 内での言及回数
            degree = sum(
                len(re.findall(re.escape(term), txt, re.IGNORECASE)) for txt in all_md_texts
            )

            # ① 度数閾値フィルター (Degree Cutoff)
            if degree >= max_hub_degree:
                glossary_hits.append(
                    {
                        "term": term,
                        "file": f"{term.lower()}.md",
                        "content": f"[[{term}]] (巨大ハブノード: 言及度数 {degree} 件のため簡易参照)",
                        "is_hub": True,
                    }
                )
                continue

            # ② 用語説明ノートのロード ＋ トークンバジェット制御
            for g_file in glossary_dir.glob("*.md"):
                g_content = g_file.read_text(encoding="utf-8")
                if term.lower() in g_content.lower() or term.lower() in g_file.stem.lower():
                    lines = [line for line in g_content.splitlines() if not line.startswith("---")]
                    snippet = "\n".join(lines[:10]).strip()
                    token_cost = len(snippet) // 3  # おおよそのトークン数概算

                    if accumulated_tokens + token_cost > max_traversal_tokens:
                        # 1-Hop トークンバジェット上限到達 -> 打ち切り
                        break

                    accumulated_tokens += token_cost
                    glossary_hits.append(
                        {
                            "term": term,
                            "file": g_file.name,
                            "content": snippet,
                            "is_hub": False,
                        }
                    )
                    break

        # LLM 用の統合プロンプトの構成
        context_blocks = ["=== メイン検索ヒット情報 ==="]
        for i, hit in enumerate(main_hits, 1):
            context_blocks.append(
                f"[{i}] タイトル: {hit.get('title')} (スコア: {hit.get('score', 0):.2f})\n"
                f"    ファイル: {hit.get('file_path')}\n"
                f"    本文抜粋: {hit.get('content')}\n"
            )

        if glossary_hits:
            context_blocks.append(
                f"=== 巡回抽出された WikiLink 用語定義 (1-Hop, トークン消費: {accumulated_tokens}/{max_traversal_tokens}) ==="
            )
            for g in glossary_hits:
                context_blocks.append(f"・[[{g['term']}]]:\n{g['content']}\n")

        full_context = "\n".join(context_blocks)

        system_prompt = (
            "あなたは LLM-Wiki ナレッジベースの高度な知識探索・回答AIです。"
            "提供された【メイン検索ヒット情報】と【巡回抽出された WikiLink 用語定義】を相互に統合・分析し、"
            "ユーザーの質問に対して概念の定義、文脈、具体内容を含む分かりやすい日本語のレポート回答を生成してください。"
            "回答中では関連する用語を [[用語名]] 形式で適宜引用・参照してください。"
        )

        user_prompt = f"ユーザーの質問: {query}\n\n{full_context}"

        try:
            answer = self.llm_client.generate_chat_completion(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
            )
        except Exception as e:
            answer = f"回答生成中にエラーが発生しました: {e}"

        return SearchResult(
            query=query,
            main_hits=main_hits,
            traversed_glossary_terms=glossary_hits,
            integrated_answer=answer,
        )

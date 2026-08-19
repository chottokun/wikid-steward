import re
import uuid
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import yaml
from filelock import FileLock, Timeout
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from wikid_steward.core.config import get_config
from wikid_steward.core.slug import generate_slug


@dataclass
class KnowledgeChunk:
    chunk_id: str
    doc_id: str
    title: str
    doc_type: str
    file_path: str
    content: str
    is_glossary: bool = False


class OpenAICompatibleEmbeddingClient:
    """Ollama, vLLM, LM Studio, OpenAI などのすべての OpenAI 互換 API サーバーから

    埋め込みベクトル (Embeddings) を統一取得する標準クライアント。
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        api_key: str = "ollama",
        model: str = "bge-small-en",
        timeout: float = 3.0,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=self.timeout)

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """テキストのリストからバッチ処理で埋め込みベクトルを生成する"""
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                response = self.client.embeddings.create(input=batch, model=self.model)
                for data in response.data:
                    all_embeddings.append(data.embedding)
            except Exception as e:
                print(
                    f"[Embedding Error] Failed to generate embedding via OpenAI-compatible API: {e}"
                )
                # セーフティフォールバック (0ベクトル)
                dim = len(all_embeddings[0]) if all_embeddings else 384
                for _ in batch:
                    all_embeddings.append([0.0] * dim)

        return all_embeddings


class QdrantKnowledgeIndexer:
    """Qdrant ベクトル DB を利用して wiki/ 配下の全ナレッジノートを

    OpenAI 互換 Embedding クライアント経由で多次元ベクトル化する標準インデクサー。
    """

    def __init__(
        self,
        location: str | None = None,
        collection_name: str | None = None,
        embedding_client: OpenAICompatibleEmbeddingClient | None = None,
    ):
        cfg = get_config()
        self.collection_name = collection_name or cfg.vector_db.collection_name
        self.location = location or cfg.vector_db.url

        # Qdrant クライアント設定
        qdrant_api_key = getattr(cfg.vector_db, "api_key", None) or None
        self._lock: FileLock | None = None

        if self.location.startswith("http://") or self.location.startswith("https://"):
            self.client = QdrantClient(url=self.location, api_key=qdrant_api_key)
        elif self.location == ":memory:":
            self.client = QdrantClient(location=":memory:")
        else:
            lock_path = Path(self.location).parent / f"{Path(self.location).name}.lock"
            self._lock = FileLock(str(lock_path), timeout=10)
            try:
                self._lock.acquire(timeout=10)
                self.client = QdrantClient(path=self.location, api_key=qdrant_api_key)
            except (Timeout, Exception) as e:
                print(
                    f"[Indexer Warning] Could not acquire Qdrant lock or open path '{self.location}': {e}"
                )
                self.client = QdrantClient(location=":memory:")

        # 汎用 OpenAI 互換 Embedding クライアント
        if embedding_client:
            self.embedding_client = embedding_client
        else:
            emb_api_key = cfg.vector_db.embedding_api_key or cfg.llm.api_key
            self.embedding_client = OpenAICompatibleEmbeddingClient(
                base_url=cfg.vector_db.embedding_base_url,
                api_key=emb_api_key,
                model=cfg.vector_db.embedding_model,
            )

        print(
            f"[Indexer] Using OpenAI-Compatible Embedding Engine -> "
            f"BaseURL: '{self.embedding_client.base_url}', Model: '{self.embedding_client.model}'"
        )

    def close(self):
        """Release Qdrant lock and close client"""
        if hasattr(self, "client") and self.client:
            try:
                self.client.close()
            except Exception:
                pass
        if hasattr(self, "_lock") and self._lock and self._lock.is_locked:
            self._lock.release()

    def __del__(self):
        self.close()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embedding クライアント経由でベクトル生成"""
        return self.embedding_client.embed_texts(texts)

    def compute_pagerank(self, wiki_dir: Path | str, damping: float = 0.85) -> dict[str, float]:
        """Wiki 内の [[WikiLink]] 構造から有向グラフ G = (V, E) を構築し、PageRank スコアを事前計算する"""
        base_path = Path(wiki_dir)
        if not base_path.exists():
            return {}

        md_files = list(base_path.glob("**/*.md"))
        if not md_files:
            return {}

        # 1. 各ファイルのノード名 (title / stem / slug) マップ作成
        file_to_id: dict[Path, str] = {}
        title_to_id: dict[str, str] = {}
        wikilink_pattern = re.compile(r"\[\[([^\]\r\n]+)\]\]")

        for md_file in md_files:
            doc_id = md_file.stem
            title = md_file.stem
            try:
                content = md_file.read_text(encoding="utf-8")
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        yaml_meta = yaml.safe_load(parts[1]) or {}
                        title = str(yaml_meta.get("title", title))
                        doc_id = str(yaml_meta.get("id", doc_id))
            except Exception:
                pass

            file_to_id[md_file] = doc_id
            title_to_id[title.strip().lower()] = doc_id
            title_to_id[doc_id.lower()] = doc_id
            title_to_id[generate_slug(title)] = doc_id

        # 2. 有向グラフの構築
        G = nx.DiGraph()
        for doc_id in set(file_to_id.values()):
            G.add_node(doc_id)

        for md_file in md_files:
            source_id = file_to_id[md_file]
            try:
                content = md_file.read_text(encoding="utf-8")
                found_links = wikilink_pattern.findall(content)
                for link in found_links:
                    term = link.split("|", 1)[0].strip()
                    term_key = term.lower()
                    target_id = title_to_id.get(term_key) or title_to_id.get(generate_slug(term))
                    if target_id and target_id != source_id:
                        G.add_edge(source_id, target_id)
            except Exception:
                pass

        if len(G.nodes) == 0:
            return {}

        # 3. PageRank 計算
        try:
            pagerank_scores = nx.pagerank(G, alpha=damping)
        except Exception as e:
            print(f"[PageRank Warning] Computation failed: {e}")
            default_val = 1.0 / len(G.nodes) if len(G.nodes) > 0 else 0.0
            pagerank_scores = {node: default_val for node in G.nodes}

        return pagerank_scores

    def _ensure_collection_exists(self, vector_size: int = 384):
        """コレクションが存在しなければ新規作成する"""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    def prune_deleted_points(self, wiki_dir: Path | str) -> int:
        """ディスク上から物理削除された Markdown ファイルに対応する Qdrant 内の孤立 Point を自動パージする"""
        base_path = Path(wiki_dir)
        if not base_path.exists():
            return 0

        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            return 0

        existing_rel_paths = {str(f.relative_to(base_path)) for f in base_path.glob("**/*.md")}

        # Qdrant から全ポイントの payload (file_path) をスクロール取得
        orphan_ids: list[str] = []
        offset = None
        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for pt in points:
                payload = pt.payload or {}
                f_path = payload.get("file_path")
                if f_path and f_path not in existing_rel_paths:
                    orphan_ids.append(str(pt.id))

            if next_offset is None or not points:
                break
            offset = next_offset

        if orphan_ids:
            from qdrant_client.models import PointIdsList

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=orphan_ids),
            )
            print(
                f"[Indexer GC] Pruned {len(orphan_ids)} orphan points from collection '{self.collection_name}'."
            )

        return len(orphan_ids)

    def index_wiki_directory(self, wiki_dir: Path | str, prune: bool = True) -> int:
        """wiki/ 配下の全 Markdown ノートを分解し、Qdrant へベクトルインデックス化する (prune=True で孤立Point自動GC)"""
        base_path = Path(wiki_dir)
        if not base_path.exists():
            return 0

        if prune:
            self.prune_deleted_points(wiki_dir=base_path)

        md_files = list(base_path.glob("**/*.md"))
        chunks: list[KnowledgeChunk] = []

        print(f"[Indexer] Scanning {len(md_files)} markdown files in {base_path}...")

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
                title = md_file.stem
                doc_type = "General Document"
                doc_id = md_file.stem
                is_glossary = "glossary" in str(md_file.parent)

                body = content
                # OKF Frontmatter の解析
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        yaml_meta = yaml.safe_load(parts[1]) or {}
                        title = str(yaml_meta.get("title", title))
                        doc_type = str(yaml_meta.get("type", doc_type))
                        doc_id = str(yaml_meta.get("id", doc_id))
                        body = parts[2].strip()

                # 段落ブロックごとに Chunk 分割
                paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
                if not paragraphs and body.strip():
                    paragraphs = [body.strip()]
                for i, para in enumerate(paragraphs):
                    chunk_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_id}_{i}_{para[:30]}"))
                    chunks.append(
                        KnowledgeChunk(
                            chunk_id=chunk_uuid,
                            doc_id=doc_id,
                            title=title,
                            doc_type=doc_type,
                            file_path=str(md_file.relative_to(base_path)),
                            content=para,
                            is_glossary=is_glossary,
                        )
                    )
            except Exception as e:
                print(f"[Indexer Skip] {md_file.name}: {e}")

        if not chunks:
            print("[Indexer] No chunks generated.")
            return 0

        print(
            f"[Indexer] Generating embeddings for {len(chunks)} chunks via OpenAI-compatible API..."
        )
        texts = [c.content for c in chunks]
        embeddings = self.embed_texts(texts)

        if not embeddings:
            return 0

        vector_size = len(embeddings[0])
        self._ensure_collection_exists(vector_size=vector_size)

        # PageRank 事前計算
        pagerank_dict = self.compute_pagerank(wiki_dir=base_path)

        points = []
        for chunk, vector in zip(chunks, embeddings):
            pr_score = pagerank_dict.get(chunk.doc_id, 0.0)
            points.append(
                PointStruct(
                    id=chunk.chunk_id,
                    vector=vector,
                    payload={
                        "doc_id": chunk.doc_id,
                        "title": chunk.title,
                        "doc_type": chunk.doc_type,
                        "file_path": chunk.file_path,
                        "content": chunk.content,
                        "is_glossary": chunk.is_glossary,
                        "pagerank_score": pr_score,
                    },
                )
            )

        print(
            f"[Indexer] Upserting {len(points)} points into Qdrant collection '{self.collection_name}' with cached PageRank..."
        )
        self.client.upsert(collection_name=self.collection_name, points=points)
        print(f"[Indexer Done] Successfully indexed {len(points)} knowledge points.")
        return len(points)

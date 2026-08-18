import uuid
from dataclasses import dataclass
from pathlib import Path

import yaml
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from wikid_steward.core.config import get_config


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
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

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
        if self.location.startswith("http://") or self.location.startswith("https://"):
            self.client = QdrantClient(url=self.location, api_key=qdrant_api_key)
        elif self.location == ":memory:":
            self.client = QdrantClient(location=":memory:")
        else:
            self.client = QdrantClient(path=self.location, api_key=qdrant_api_key)

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

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embedding クライアント経由でベクトル生成"""
        return self.embedding_client.embed_texts(texts)

    def _ensure_collection_exists(self, vector_size: int = 384):
        """コレクションが存在しなければ新規作成する"""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    def index_wiki_directory(self, wiki_dir: Path | str) -> int:
        """wiki/ 配下の全 Markdown ノートを分解し、Qdrant へベクトルインデックス化する"""
        base_path = Path(wiki_dir)
        if not base_path.exists():
            return 0

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

                # OKF Frontmatter の解析
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        yaml_meta = yaml.safe_load(parts[1]) or {}
                        title = str(yaml_meta.get("title", title))
                        doc_type = str(yaml_meta.get("type", doc_type))
                        doc_id = str(yaml_meta.get("id", doc_id))

                # 段落ブロックごとに Chunk 分割
                paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
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

        points = []
        for chunk, vector in zip(chunks, embeddings):
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
                    },
                )
            )

        print(
            f"[Indexer] Upserting {len(points)} points into Qdrant collection '{self.collection_name}'..."
        )
        self.client.upsert(collection_name=self.collection_name, points=points)
        print(f"[Indexer Done] Successfully indexed {len(points)} knowledge points.")
        return len(points)

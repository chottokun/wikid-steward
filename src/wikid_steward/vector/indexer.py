import uuid
from dataclasses import dataclass
from pathlib import Path
import yaml
from fastembed import TextEmbedding
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


class QdrantKnowledgeIndexer:
    """Qdrant ベクトル DB を利用して wiki/ 配下の全ナレッジノートおよび

    VLM 要約・構造化要素をベクトルインデックス化するモジュール。
    """

    def __init__(
        self,
        location: str | None = None,
        collection_name: str | None = None,
        embedding_model_name: str = "BAAI/bge-small-en-v1.5",
    ):
        cfg = get_config()
        self.collection_name = collection_name or cfg.vector_db.collection_name
        self.location = location or cfg.vector_db.url

        # インメモリまたはローカル/リモート Qdrant クライアント
        if self.location.startswith("http://") or self.location.startswith("https://"):
            self.client = QdrantClient(url=self.location)
        elif self.location == ":memory:":
            self.client = QdrantClient(location=":memory:")
        else:
            self.client = QdrantClient(path=self.location)

        # FastEmbed による高速・軽量ローカル埋め込みモデル
        self.embedding_model = TextEmbedding(model_name=embedding_model_name)

    def _ensure_collection_exists(self, vector_size: int = 384):
        """コレクションが存在しなければ新規作成する"""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    def index_wiki_directory(self, wiki_dir: Path | str) -> int:
        """wiki/ ディレクトリ配下の全 Markdown ノートを全自動でベクトルインデックス化する"""
        base_path = Path(wiki_dir)
        if not base_path.exists():
            return 0

        md_files = list(base_path.glob("**/*.md"))
        chunks: list[KnowledgeChunk] = []

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
                        title = yaml_meta.get("title", title)
                        doc_type = yaml_meta.get("type", doc_type)
                        doc_id = yaml_meta.get("id", doc_id)

                # 段落ブロックごとに Chunk 分割
                paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
                for i, para in enumerate(paragraphs):
                    chunk_uuid = str(
                        uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_id}_{i}_{para[:30]}")
                    )
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
                print(f"Indexing skip for {md_file.name}: {e}")

        if not chunks:
            return 0

        # テキストの埋め込みベクトルをバッチ生成
        texts = [c.content for c in chunks]
        embeddings = list(self.embedding_model.embed(texts))
        vector_size = len(embeddings[0])

        self._ensure_collection_exists(vector_size=vector_size)

        points = []
        for chunk, vector in zip(chunks, embeddings):
            points.append(
                PointStruct(
                    id=chunk.chunk_id,
                    vector=vector.tolist(),
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

        # Qdrant へ一括 Upsert 登録
        self.client.upsert(collection_name=self.collection_name, points=points)
        return len(points)

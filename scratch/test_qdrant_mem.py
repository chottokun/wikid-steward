from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

def test_qdrant_mem():
    client = QdrantClient(location=":memory:")
    client.create_collection(
        collection_name="test_col",
        vectors_config=VectorParams(size=4, distance=Distance.COSINE)
    )

    client.upsert(
        collection_name="test_col",
        points=[
            PointStruct(id=1, vector=[0.1, 0.2, 0.3, 0.4], payload={"text": "hello"}),
            PointStruct(id=2, vector=[0.9, 0.8, 0.7, 0.6], payload={"text": "world"})
        ]
    )

    # 1. query_points
    res1 = client.query_points(collection_name="test_col", query=[0.1, 0.2, 0.3, 0.4], limit=2)
    print("query_points points count:", len(res1.points))
    for p in res1.points:
        print("  point payload:", p.payload)

    # 2. search (旧API)
    try:
        res2 = client.search(collection_name="test_col", query_vector=[0.1, 0.2, 0.3, 0.4], limit=2)
        print("search count:", len(res2))
    except Exception as e:
        print("search API exception:", e)

if __name__ == "__main__":
    test_qdrant_mem()

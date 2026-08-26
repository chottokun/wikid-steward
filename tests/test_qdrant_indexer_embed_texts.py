from unittest.mock import MagicMock

from wikid_steward.vector.indexer import QdrantKnowledgeIndexer


def test_embed_texts_normal():
    """Test embed_texts delegates to embedding_client and returns vectors for non-empty text list."""
    mock_client = MagicMock()
    mock_client.embed_texts.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    indexer = QdrantKnowledgeIndexer(location=":memory:", embedding_client=mock_client)
    input_texts = ["Hello world", "Qdrant knowledge indexer"]
    result = indexer.embed_texts(input_texts)

    mock_client.embed_texts.assert_called_once_with(input_texts)
    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]


def test_embed_texts_empty():
    """Test embed_texts handles empty list of input texts correctly."""
    mock_client = MagicMock()
    mock_client.embed_texts.return_value = []

    indexer = QdrantKnowledgeIndexer(location=":memory:", embedding_client=mock_client)
    result = indexer.embed_texts([])

    mock_client.embed_texts.assert_called_once_with([])
    assert result == []


def test_embed_texts_single_item():
    """Test embed_texts with a single text string."""
    mock_client = MagicMock()
    mock_client.embed_texts.return_value = [[1.0, 0.0, -1.0]]

    indexer = QdrantKnowledgeIndexer(location=":memory:", embedding_client=mock_client)
    result = indexer.embed_texts(["Single paragraph"])

    mock_client.embed_texts.assert_called_once_with(["Single paragraph"])
    assert result == [[1.0, 0.0, -1.0]]

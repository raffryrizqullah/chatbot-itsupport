"""
Unit tests for Redis document store.

Tests Redis-based document storage with serialization and mocked Redis client.
"""

import pytest
from unittest.mock import MagicMock, patch
import json

from app.services.redis_store import (
    RedisDocStore,
    _serialize_to_json,
    _deserialize_from_json,
)
from app.core.exceptions import RedisStoreError
from langchain_core.documents import Document


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client for testing."""
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.mset.return_value = True
    mock_client.mget.return_value = []
    mock_client.delete.return_value = 0
    mock_client.scan_iter.return_value = iter([])
    return mock_client


@pytest.mark.unit
class TestSerializationFunctions:
    """Test suite for serialization helper functions."""

    def test_serialize_document_to_json(self):
        """Test serializing Document object to JSON."""
        doc = Document(page_content="Test content", metadata={"source": "test.pdf"})
        json_str = _serialize_to_json(doc)

        data = json.loads(json_str)
        assert data["_type"] == "Document"
        assert data["page_content"] == "Test content"
        assert data["metadata"]["source"] == "test.pdf"

    def test_serialize_string_to_json(self):
        """Test serializing string to JSON."""
        text = "Simple text"
        json_str = _serialize_to_json(text)

        data = json.loads(json_str)
        assert data["_type"] == "str"
        assert data["data"] == "Simple text"

    def test_deserialize_document_from_json(self):
        """Test deserializing Document from JSON."""
        json_str = json.dumps({
            "_type": "Document",
            "page_content": "Test content",
            "metadata": {"source": "test.pdf"}
        })

        doc = _deserialize_from_json(json_str)

        assert isinstance(doc, Document)
        assert doc.page_content == "Test content"
        assert doc.metadata["source"] == "test.pdf"

    def test_deserialize_string_from_json(self):
        """Test deserializing string from JSON."""
        json_str = json.dumps({"_type": "str", "data": "Simple text"})

        text = _deserialize_from_json(json_str)

        assert text == "Simple text"


@pytest.mark.unit
class TestRedisDocStore:
    """Test suite for Redis document store."""

    def test_redis_store_initialization_success(self, mock_redis_client):
        """Test successful Redis store initialization."""
        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            assert store.client is not None
            assert store.namespace == "rag:doc"
            mock_redis_client.ping.assert_called_once()

    def test_redis_store_initialization_custom_namespace(self, mock_redis_client):
        """Test Redis store initialization with custom namespace."""
        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore(namespace="custom:namespace")

            assert store.namespace == "custom:namespace"

    def test_redis_store_initialization_connection_error(self):
        """Test that Redis connection error raises RedisStoreError."""
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("Connection refused")

        with patch("app.services.redis_store.redis.Redis", return_value=mock_client):
            with pytest.raises(RedisStoreError, match="Failed to connect to Redis"):
                RedisDocStore()

    def test_make_key_creates_namespaced_key(self, mock_redis_client):
        """Test that _make_key creates correct namespaced key."""
        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()
            key = store._make_key("doc123")

            assert key == "rag:doc:doc123"

    def test_mset_success(self, mock_redis_client):
        """Test successfully storing multiple documents."""
        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            doc1 = Document(page_content="Content 1", metadata={})
            doc2 = Document(page_content="Content 2", metadata={})

            pairs = [("id1", doc1), ("id2", doc2)]
            store.mset(pairs)

            # Verify mset was called
            mock_redis_client.mset.assert_called_once()

    def test_mset_empty_pairs(self, mock_redis_client):
        """Test mset with empty pairs does nothing."""
        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            store.mset([])

            # Verify mset was NOT called
            mock_redis_client.mset.assert_not_called()

    def test_mset_raises_error_on_failure(self, mock_redis_client):
        """Test that mset raises RedisStoreError on failure."""
        mock_redis_client.mset.side_effect = Exception("Redis error")

        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            doc = Document(page_content="Content", metadata={})

            with pytest.raises(RedisStoreError, match="Failed to store documents"):
                store.mset([("id1", doc)])

    def test_mget_success(self, mock_redis_client):
        """Test successfully retrieving multiple documents."""
        # Mock Redis returning serialized documents
        doc_json = json.dumps({"_type": "Document", "page_content": "Content", "metadata": {}})
        mock_redis_client.mget.return_value = [doc_json, doc_json]

        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            results = store.mget(["id1", "id2"])

            assert len(results) == 2
            assert all(isinstance(r, Document) for r in results)

    def test_mget_empty_keys(self, mock_redis_client):
        """Test mget with empty keys returns empty list."""
        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            results = store.mget([])

            assert results == []

    def test_mget_handles_none_values(self, mock_redis_client):
        """Test mget handles None values from Redis."""
        mock_redis_client.mget.return_value = [None, None]

        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            results = store.mget(["id1", "id2"])

            assert len(results) == 2
            assert all(r is None for r in results)

    def test_mget_raises_error_on_failure(self, mock_redis_client):
        """Test that mget raises RedisStoreError on failure."""
        mock_redis_client.mget.side_effect = Exception("Redis error")

        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            with pytest.raises(RedisStoreError, match="Failed to retrieve documents"):
                store.mget(["id1"])

    def test_mdelete_success(self, mock_redis_client):
        """Test successfully deleting multiple documents."""
        mock_redis_client.delete.return_value = 2

        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            store.mdelete(["id1", "id2"])

            # Verify delete was called
            mock_redis_client.delete.assert_called_once()

    def test_mdelete_empty_keys(self, mock_redis_client):
        """Test mdelete with empty keys does nothing."""
        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            store.mdelete([])

            # Verify delete was NOT called
            mock_redis_client.delete.assert_not_called()

    def test_mdelete_raises_error_on_failure(self, mock_redis_client):
        """Test that mdelete raises RedisStoreError on failure."""
        mock_redis_client.delete.side_effect = Exception("Redis error")

        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            with pytest.raises(RedisStoreError, match="Failed to delete documents"):
                store.mdelete(["id1"])

    def test_yield_keys_no_prefix(self, mock_redis_client):
        """Test yielding all keys without prefix."""
        mock_redis_client.scan_iter.return_value = iter(["rag:doc:id1", "rag:doc:id2"])

        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            keys = list(store.yield_keys())

            assert len(keys) == 2
            assert "id1" in keys
            assert "id2" in keys

    def test_yield_keys_with_prefix(self, mock_redis_client):
        """Test yielding keys with specific prefix."""
        mock_redis_client.scan_iter.return_value = iter(["rag:doc:user:id1", "rag:doc:user:id2"])

        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            keys = list(store.yield_keys(prefix="user"))

            assert len(keys) == 2

    def test_yield_keys_empty_result(self, mock_redis_client):
        """Test yielding keys when no keys exist."""
        mock_redis_client.scan_iter.return_value = iter([])

        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            keys = list(store.yield_keys())

            assert keys == []

    def test_yield_keys_raises_error_on_failure(self, mock_redis_client):
        """Test that yield_keys raises RedisStoreError on failure."""
        mock_redis_client.scan_iter.side_effect = Exception("Redis error")

        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            with pytest.raises(RedisStoreError, match="Failed to retrieve keys"):
                list(store.yield_keys())

    def test_clear_success(self, mock_redis_client):
        """Test successfully clearing all documents."""
        mock_redis_client.scan_iter.return_value = iter(["rag:doc:id1", "rag:doc:id2"])
        mock_redis_client.delete.return_value = 2

        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            store.clear()

            # Verify delete was called
            mock_redis_client.delete.assert_called_once()

    def test_clear_no_documents(self, mock_redis_client):
        """Test clearing when no documents exist."""
        mock_redis_client.scan_iter.return_value = iter([])

        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            store.clear()

            # Verify delete was NOT called
            mock_redis_client.delete.assert_not_called()

    def test_clear_raises_error_on_failure(self, mock_redis_client):
        """Test that clear raises RedisStoreError on failure."""
        mock_redis_client.scan_iter.side_effect = Exception("Redis error")

        with patch("app.services.redis_store.redis.Redis", return_value=mock_redis_client):
            store = RedisDocStore()

            with pytest.raises(RedisStoreError, match="Failed to clear Redis docstore"):
                store.clear()

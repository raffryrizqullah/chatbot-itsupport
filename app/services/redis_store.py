"""
Redis-based document store for persistent storage.

This module implements a Redis-backed document store that persists
retrieved documents across server restarts, replacing InMemoryStore.
"""

from typing import List, Tuple, Any, Optional, Sequence, Iterator
import redis
import json
import logging
from langchain_core.stores import BaseStore
from langchain_core.documents import Document
from app.core.config import settings
from app.core.exceptions import RedisStoreError

logger = logging.getLogger(__name__)


def _serialize_to_json(value: Any) -> str:
    """
    Safely serialize document to JSON.

    Args:
        value: Document or string to serialize.

    Returns:
        JSON string representation.
    """
    if isinstance(value, Document):
        return json.dumps({
            "_type": "Document",
            "page_content": value.page_content,
            "metadata": value.metadata
        })
    # Handle other types (strings, base64 images, etc.)
    return json.dumps({
        "_type": "str",
        "data": str(value)
    })


def _deserialize_from_json(json_str: str) -> Any:
    """
    Safely deserialize document from JSON.

    Args:
        json_str: JSON string to deserialize.

    Returns:
        Deserialized Document or string.
    """
    data = json.loads(json_str)
    if data.get("_type") == "Document":
        return Document(
            page_content=data["page_content"],
            metadata=data["metadata"]
        )
    # Return string data for other types
    return data.get("data", "")


class RedisDocStore(BaseStore):
    """
    Redis-based document store for RAG pipeline.

    Stores original documents (text, tables, images) in Redis using
    JSON serialization for safe persistence across application restarts.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None,
        namespace: str = "rag:doc"
<<<<<<< HEAD
    ):
=======
    ) -> None:
>>>>>>> bb677be (feat : update logging error)
        """
        Initialize Redis document store.

        Args:
            host: Redis host (defaults to settings.redis_host).
            port: Redis port (defaults to settings.redis_port).
            db: Redis database number (defaults to settings.redis_db).
            password: Redis password (defaults to settings.redis_password).
            namespace: Key namespace prefix for document storage.
        """
        self.namespace = namespace

        # Use settings as defaults
        self.host = host or settings.redis_host
        self.port = port or settings.redis_port
        self.db = db or settings.redis_db
        self.password = password or settings.redis_password

        # Initialize Redis client
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=True  # Decode to strings for JSON
        )

        # Test connection
        try:
            self.client.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}/{self.db}")
        except redis.ConnectionError as e:
            msg = f"Failed to connect to Redis: {str(e)}"
            logger.error(msg)
            raise RedisStoreError(msg)

    def _make_key(self, doc_id: str) -> str:
        """
        Create a namespaced Redis key.

        Args:
            doc_id: Document identifier.

        Returns:
            Namespaced key string.
        """
        return f"{self.namespace}:{doc_id}"

    def mset(self, key_value_pairs: Sequence[Tuple[str, Any]]) -> None:
        """
        Set multiple documents in Redis.

        Args:
            key_value_pairs: Sequence of (key, value) tuples to store.
        """
        try:
            if not key_value_pairs:
                return

            # Serialize values with JSON and create namespaced keys
            redis_pairs = {}
            for key, value in key_value_pairs:
                namespaced_key = self._make_key(key)
                serialized_value = _serialize_to_json(value)
                redis_pairs[namespaced_key] = serialized_value

            # Store in Redis
            self.client.mset(redis_pairs)
            logger.info(f"Stored {len(redis_pairs)} documents in Redis")

        except Exception as e:
            msg = f"Failed to store documents in Redis: {str(e)}"
            logger.error(msg)
            raise RedisStoreError(msg)

    def mget(self, keys: Sequence[str]) -> List[Any]:
        """
        Retrieve multiple documents from Redis.

        Args:
            keys: Sequence of document IDs to retrieve.

        Returns:
            List of deserialized document values.
        """
        try:
            if not keys:
                return []

            # Create namespaced keys
            namespaced_keys = [self._make_key(key) for key in keys]

            # Retrieve from Redis
            values = self.client.mget(namespaced_keys)

            # Deserialize values
            results = []
            for value in values:
                if value is not None:
                    results.append(_deserialize_from_json(value))
                else:
                    results.append(None)

            logger.info(f"Retrieved {len(results)} documents from Redis")
            return results

        except Exception as e:
            msg = f"Failed to retrieve documents from Redis: {str(e)}"
            logger.error(msg)
            raise RedisStoreError(msg)

    def mdelete(self, keys: Sequence[str]) -> None:
        """
        Delete multiple documents from Redis.

        Args:
            keys: Sequence of document IDs to delete.
        """
        try:
            if not keys:
                return

            # Create namespaced keys
            namespaced_keys = [self._make_key(key) for key in keys]

            # Delete from Redis
            deleted_count = self.client.delete(*namespaced_keys)
            logger.info(f"Deleted {deleted_count} documents from Redis")

        except Exception as e:
            msg = f"Failed to delete documents from Redis: {str(e)}"
            logger.error(msg)
            raise RedisStoreError(msg)

    def yield_keys(self, prefix: Optional[str] = None) -> Iterator[str]:
        """
        Retrieve all document keys, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter keys.

        Yields:
            Document IDs (without namespace prefix).
        """
        try:
            # Build scan pattern
            if prefix:
                pattern = f"{self.namespace}:{prefix}*"
            else:
                pattern = f"{self.namespace}:*"

            # Scan for keys and yield them
            count = 0
            for key in self.client.scan_iter(match=pattern):
                # Remove namespace prefix (key is already string due to decode_responses=True)
                doc_id = key.replace(f"{self.namespace}:", "")
                yield doc_id
                count += 1

            logger.info(f"Yielded {count} keys with pattern {pattern}")

        except Exception as e:
            msg = f"Failed to retrieve keys from Redis: {str(e)}"
            logger.error(msg)
            raise RedisStoreError(msg)

    def clear(self) -> None:
        """
        Clear all documents in the namespace.

        WARNING: This will delete all documents with the namespace prefix.
        """
        try:
            # Convert iterator to list for deletion
            keys = list(self.yield_keys())
            if keys:
                self.mdelete(keys)
                logger.info(f"Cleared {len(keys)} documents from Redis")
            else:
                logger.info("No documents to clear")

        except Exception as e:
            msg = f"Failed to clear Redis docstore: {str(e)}"
            logger.error(msg)
            raise RedisStoreError(msg)

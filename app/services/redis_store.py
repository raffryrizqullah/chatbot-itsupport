"""
Redis-based document store for persistent storage.

This module implements a Redis-backed document store that persists
retrieved documents across server restarts, replacing InMemoryStore.
"""

from typing import List, Tuple, Any, Optional, Sequence, Iterator
import redis
import pickle
import logging
from langchain_core.stores import BaseStore
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisDocStore(BaseStore):
    """
    Redis-based document store for RAG pipeline.

    Stores original documents (text, tables, images) in Redis using
    pickle serialization for persistence across application restarts.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None,
        namespace: str = "rag:doc"
    ):
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
            decode_responses=False  # We need bytes for pickle
        )

        # Test connection
        try:
            self.client.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}/{self.db}")
        except redis.ConnectionError as e:
            msg = f"Failed to connect to Redis: {str(e)}"
            logger.error(msg)
            raise Exception(msg)

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

            # Serialize values with pickle and create namespaced keys
            redis_pairs = {}
            for key, value in key_value_pairs:
                namespaced_key = self._make_key(key)
                serialized_value = pickle.dumps(value)
                redis_pairs[namespaced_key] = serialized_value

            # Store in Redis
            self.client.mset(redis_pairs)
            logger.info(f"Stored {len(redis_pairs)} documents in Redis")

        except Exception as e:
            msg = f"Failed to store documents in Redis: {str(e)}"
            logger.error(msg)
            raise Exception(msg)

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
                    results.append(pickle.loads(value))
                else:
                    results.append(None)

            logger.info(f"Retrieved {len(results)} documents from Redis")
            return results

        except Exception as e:
            msg = f"Failed to retrieve documents from Redis: {str(e)}"
            logger.error(msg)
            raise Exception(msg)

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
            raise Exception(msg)

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
                # Remove namespace prefix
                doc_id = key.decode('utf-8').replace(f"{self.namespace}:", "")
                yield doc_id
                count += 1

            logger.info(f"Yielded {count} keys with pattern {pattern}")

        except Exception as e:
            msg = f"Failed to retrieve keys from Redis: {str(e)}"
            logger.error(msg)
            raise Exception(msg)

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
            raise Exception(msg)

"""
Chat memory service using Redis for conversation history.

This module provides short-term conversational memory for chatbot sessions,
storing chat history in Redis with TTL for automatic cleanup.
"""

from typing import List, Dict, Any, Optional
import redis
import json
import logging
from datetime import datetime
from app.core.config import settings
from app.core.exceptions import ChatMemoryError

logger = logging.getLogger(__name__)


class ChatMemoryService:
    """
    Redis-based chat memory service for conversational history.

    Stores chat messages per session with automatic TTL expiration.
    Supports message trimming to prevent context overflow.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None,
<<<<<<< HEAD
    ):
=======
    ) -> None:
>>>>>>> bb677be (feat : update logging error)
        """
        Initialize chat memory service.

        Args:
            host: Redis host (defaults to settings.redis_host).
            port: Redis port (defaults to settings.redis_port).
            db: Redis database number (defaults to settings.redis_db).
            password: Redis password (defaults to settings.redis_password).
        """
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
            decode_responses=True,  # Auto-decode to strings
        )

        # Test connection
        try:
            self.client.ping()
            logger.info(f"Chat memory connected to Redis at {self.host}:{self.port}")
        except redis.ConnectionError as e:
            msg = f"Failed to connect to Redis for chat memory: {str(e)}"
            logger.error(msg)
            raise ChatMemoryError(msg)

    def _make_key(self, session_id: str) -> str:
        """
        Create Redis key for session.

        Args:
            session_id: Session identifier.

        Returns:
            Redis key string.
        """
        return f"chat_history:{session_id}"

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get chat history for a session.

        Args:
            session_id: Session identifier.

        Returns:
            List of message dictionaries with 'role' and 'content' keys.
            Returns empty list if no history exists.
        """
        try:
            key = self._make_key(session_id)
            history_json = self.client.get(key)

            if not history_json:
                logger.info(f"No chat history found for session: {session_id}")
                return []

            history = json.loads(history_json)
            logger.info(f"Retrieved {len(history)} messages for session: {session_id}")
            return history

        except Exception as e:
            msg = f"Failed to get chat history for {session_id}: {str(e)}"
            logger.error(msg)
            return []  # Return empty list on error, don't break the flow

    def add_message(
        self, session_id: str, role: str, content: str, timestamp: Optional[str] = None
    ) -> None:
        """
        Add a message to chat history.

        Args:
            session_id: Session identifier.
            role: Message role (``'user'`` or ``'assistant'``).
            content: Message content.
            timestamp: Optional timestamp (ISO format). Defaults to current time.
        """
        try:
            key = self._make_key(session_id)

            # Get existing history
            history = self.get_history(session_id)

            # Add new message
            message = {
                "role": role,
                "content": content,
                "timestamp": timestamp or datetime.utcnow().isoformat(),
            }
            history.append(message)

            # Trim history if needed
            history = self._trim_history(history)

            # Save to Redis with TTL
            self.client.setex(
                key, settings.chat_history_ttl, json.dumps(history, ensure_ascii=False)
            )

            logger.info(
                f"Added {role} message to session {session_id} (total: {len(history)} messages)"
            )

        except Exception as e:
            msg = f"Failed to add message to {session_id}: {str(e)}"
            logger.error(msg)
            # Don't raise exception, just log error

    def add_exchange(
        self, session_id: str, user_message: str, assistant_message: str
    ) -> None:
        """
        Add a complete exchange (user question + assistant answer) to history.

        Args:
            session_id: Session identifier.
            user_message: User's question.
            assistant_message: Assistant's answer.
        """
        try:
            key = self._make_key(session_id)

            # Get existing history
            history = self.get_history(session_id)

            # Add both messages
            timestamp = datetime.utcnow().isoformat()
            history.append(
                {"role": "user", "content": user_message, "timestamp": timestamp}
            )
            history.append(
                {
                    "role": "assistant",
                    "content": assistant_message,
                    "timestamp": timestamp,
                }
            )

            # Trim history if needed
            history = self._trim_history(history)

            # Save to Redis with TTL
            self.client.setex(
                key, settings.chat_history_ttl, json.dumps(history, ensure_ascii=False)
            )

            logger.info(
                f"Added exchange to session {session_id} (total: {len(history)} messages)"
            )

        except Exception as e:
            msg = f"Failed to add exchange to {session_id}: {str(e)}"
            logger.error(msg)

    def clear_history(self, session_id: str) -> bool:
        """
        Clear chat history for a session.

        Args:
            session_id: Session identifier.

        Returns:
            True if history was deleted, False if no history existed.
        """
        try:
            key = self._make_key(session_id)
            deleted = self.client.delete(key)

            if deleted:
                logger.info(f"Cleared chat history for session: {session_id}")
                return True
            else:
                logger.info(f"No chat history to clear for session: {session_id}")
                return False

        except Exception as e:
            msg = f"Failed to clear history for {session_id}: {str(e)}"
            logger.error(msg)
            return False

<<<<<<< HEAD
=======
    def list_sessions(self, limit: Optional[int] = None) -> List[str]:
        """
        List chat session identifiers stored in Redis.

        Args:
            limit: Optional maximum number of session IDs to return.

        Returns:
            Sorted list of session IDs.
        """
        try:
            pattern = self._make_key("*")
            sessions: List[str] = []

            for key in self.client.scan_iter(match=pattern):
                # Keys follow chat_history:<session_id>
                session_id = key.split(":", 1)[1] if ":" in key else key
                sessions.append(session_id)

                if limit is not None and len(sessions) >= limit:
                    break

            sessions.sort()
            logger.info(f"Listed {len(sessions)} chat sessions")
            return sessions

        except Exception as e:
            msg = f"Failed to list chat sessions: {str(e)}"
            logger.error(msg)
            return []

>>>>>>> bb677be (feat : update logging error)
    def _trim_history(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Trim history to keep only last N messages.

        Args:
            history: List of message dictionaries.

        Returns:
            Trimmed history list.
        """
        max_messages = settings.chat_max_messages

        if len(history) > max_messages:
            trimmed = history[-max_messages:]
            logger.info(
                f"Trimmed history from {len(history)} to {len(trimmed)} messages"
            )
            return trimmed

        return history

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """
        Get information about a session.

        Args:
            session_id: Session identifier.

        Returns:
            Dictionary with session info (exists, message_count, ttl).
        """
        try:
            key = self._make_key(session_id)
            exists = self.client.exists(key)

            if not exists:
                return {
                    "exists": False,
                    "message_count": 0,
                    "ttl": None,
                }

            history = self.get_history(session_id)
            ttl = self.client.ttl(key)

            return {
                "exists": True,
                "message_count": len(history),
                "ttl": ttl if ttl > 0 else None,
            }

        except Exception as e:
<<<<<<< HEAD
            logger.error(f"Failed to get session info for {session_id}: {str(e)}")
=======
            msg = f"Failed to get session info for {session_id}: {str(e)}"
            logger.error(msg)
>>>>>>> bb677be (feat : update logging error)
            return {"exists": False, "message_count": 0, "ttl": None}

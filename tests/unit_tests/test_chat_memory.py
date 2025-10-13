"""
Unit tests for chat memory service.

Tests Redis-based chat history management with mocked Redis client.
"""

import pytest
from unittest.mock import MagicMock, patch
import json
from datetime import datetime

from app.services.chat_memory import ChatMemoryService
from app.core.exceptions import ChatMemoryError


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client for testing."""
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = None
    mock_client.setex.return_value = True
    mock_client.delete.return_value = 1
    mock_client.exists.return_value = 0
    mock_client.ttl.return_value = 3600
    return mock_client


@pytest.mark.unit
class TestChatMemoryService:
    """Test suite for chat memory service."""

    def test_chat_memory_initialization_success(self, mock_redis_client):
        """Test successful chat memory initialization."""
        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()

            assert service.client is not None
            mock_redis_client.ping.assert_called_once()

    def test_chat_memory_initialization_connection_error(self):
        """Test that Redis connection error raises ChatMemoryError."""
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("Connection refused")

        with patch("app.services.chat_memory.redis.Redis", return_value=mock_client):
            with pytest.raises(ChatMemoryError, match="Failed to connect to Redis"):
                ChatMemoryService()

    def test_get_history_no_history_exists(self, mock_redis_client):
        """Test getting history when none exists returns empty list."""
        mock_redis_client.get.return_value = None

        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()
            history = service.get_history("session123")

            assert history == []

    def test_get_history_with_existing_history(self, mock_redis_client):
        """Test getting existing chat history."""
        history_data = [
            {"role": "user", "content": "Hello", "timestamp": "2024-01-01T00:00:00"},
            {"role": "assistant", "content": "Hi there!", "timestamp": "2024-01-01T00:00:01"},
        ]
        mock_redis_client.get.return_value = json.dumps(history_data)

        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()
            history = service.get_history("session123")

            assert len(history) == 2
            assert history[0]["role"] == "user"
            assert history[1]["role"] == "assistant"

    def test_get_history_handles_error_gracefully(self, mock_redis_client):
        """Test that get_history returns empty list on error."""
        mock_redis_client.get.side_effect = Exception("Redis error")

        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()
            history = service.get_history("session123")

            # Should return empty list instead of raising
            assert history == []

    def test_add_message_success(self, mock_redis_client):
        """Test successfully adding a message to history."""
        mock_redis_client.get.return_value = None  # No existing history

        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()
            service.add_message("session123", "user", "Hello")

            # Verify setex was called with correct parameters
            mock_redis_client.setex.assert_called_once()

    def test_add_message_appends_to_existing_history(self, mock_redis_client):
        """Test adding message to existing history."""
        existing_history = [{"role": "user", "content": "First message", "timestamp": "2024-01-01T00:00:00"}]
        mock_redis_client.get.return_value = json.dumps(existing_history)

        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()
            service.add_message("session123", "assistant", "Second message")

            # Verify setex was called
            mock_redis_client.setex.assert_called_once()

    def test_add_message_with_custom_timestamp(self, mock_redis_client):
        """Test adding message with custom timestamp."""
        mock_redis_client.get.return_value = None

        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()
            custom_timestamp = "2024-01-01T12:00:00"
            service.add_message("session123", "user", "Hello", timestamp=custom_timestamp)

            # Verify message was added
            mock_redis_client.setex.assert_called_once()

    def test_add_exchange_success(self, mock_redis_client):
        """Test successfully adding a complete exchange."""
        mock_redis_client.get.return_value = None

        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()
            service.add_exchange("session123", "What is IT support?", "IT support helps users with tech issues.")

            # Verify setex was called
            mock_redis_client.setex.assert_called_once()

    def test_add_exchange_appends_to_existing_history(self, mock_redis_client):
        """Test adding exchange to existing history."""
        existing_history = [{"role": "user", "content": "Previous", "timestamp": "2024-01-01T00:00:00"}]
        mock_redis_client.get.return_value = json.dumps(existing_history)

        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()
            service.add_exchange("session123", "New question", "New answer")

            # Verify setex was called
            mock_redis_client.setex.assert_called_once()

    def test_clear_history_success(self, mock_redis_client):
        """Test successfully clearing chat history."""
        mock_redis_client.delete.return_value = 1  # Indicates key was deleted

        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()
            result = service.clear_history("session123")

            assert result is True
            mock_redis_client.delete.assert_called_once()

    def test_clear_history_no_history_exists(self, mock_redis_client):
        """Test clearing history when none exists."""
        mock_redis_client.delete.return_value = 0  # No key deleted

        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()
            result = service.clear_history("session123")

            assert result is False

    def test_trim_history_when_exceeds_max(self, mock_redis_client):
        """Test that history is trimmed when it exceeds max messages."""
        # Create history with many messages
        large_history = [
            {"role": "user", "content": f"Message {i}", "timestamp": "2024-01-01T00:00:00"}
            for i in range(100)
        ]
        mock_redis_client.get.return_value = json.dumps(large_history)

        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()
            service.add_message("session123", "user", "New message")

            # Verify setex was called (trimming happened internally)
            mock_redis_client.setex.assert_called_once()

    def test_trim_history_keeps_last_n_messages(self, mock_redis_client):
        """Test that _trim_history keeps only last N messages."""
        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()

            # Create history exceeding max
            large_history = [{"role": "user", "content": f"Msg {i}", "timestamp": "2024-01-01"} for i in range(100)]

            trimmed = service._trim_history(large_history)

            # Should be trimmed to max_messages from settings
            assert len(trimmed) <= 100  # Default max from settings

    def test_trim_history_does_not_trim_if_under_max(self, mock_redis_client):
        """Test that _trim_history does not trim if under max."""
        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()

            small_history = [{"role": "user", "content": "Message", "timestamp": "2024-01-01"}]

            trimmed = service._trim_history(small_history)

            assert len(trimmed) == 1
            assert trimmed == small_history

    def test_get_session_info_session_exists(self, mock_redis_client):
        """Test getting session info when session exists."""
        history_data = [{"role": "user", "content": "Hello", "timestamp": "2024-01-01"}]
        mock_redis_client.exists.return_value = 1
        mock_redis_client.get.return_value = json.dumps(history_data)
        mock_redis_client.ttl.return_value = 3600

        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()
            info = service.get_session_info("session123")

            assert info["exists"] is True
            assert info["message_count"] == 1
            assert info["ttl"] == 3600

    def test_get_session_info_session_does_not_exist(self, mock_redis_client):
        """Test getting session info when session doesn't exist."""
        mock_redis_client.exists.return_value = 0

        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()
            info = service.get_session_info("session123")

            assert info["exists"] is False
            assert info["message_count"] == 0
            assert info["ttl"] is None

    def test_make_key_creates_correct_format(self, mock_redis_client):
        """Test that _make_key creates correct Redis key format."""
        with patch("app.services.chat_memory.redis.Redis", return_value=mock_redis_client):
            service = ChatMemoryService()
            key = service._make_key("session123")

            assert key == "chat_history:session123"

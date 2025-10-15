"""
Application configuration and settings.

This module manages all environment variables and application settings
using Pydantic Settings for type safety and validation.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from urllib.parse import quote_plus, urlsplit, urlunsplit


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden by environment variables with the same name.
    """

    # API Settings
    app_name: str = "Multi-modal RAG API"
    app_version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"

    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-5-2025-08-07"
    openai_temperature: float = 0.5

    # Pinecone Configuration
    pinecone_api_key: str
    pinecone_environment: str = "us-east-1"
    pinecone_index_name: str = "multimodal-rag"
    pinecone_dimension: int = 3072  # text-embedding-3-large dimension
    pinecone_metric: str = "cosine"

    # PDF Processing Configuration
    pdf_upload_dir: str = "./content"  # Deprecated: Use R2 storage instead
    pdf_max_file_size: int = 10485760  # 10 MB (10 * 1024 * 1024)
    pdf_chunking_strategy: str = "by_title"
    pdf_max_characters: int = 10000
    pdf_combine_text_under_n_chars: int = 2000
    pdf_new_after_n_chars: int = 6000
    pdf_retention_days: int = 7  # Auto-delete files older than this

    # OCR / Tesseract Configuration
    # Comma or plus-separated language codes (e.g., "eng", "ind", "eng+ind")
    ocr_languages: str = "eng"

    # Cloudflare R2 Storage Configuration
    r2_account_id: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket_name: str

    @property
    def r2_endpoint_url(self) -> str:
        """Generate R2 endpoint URL from account ID."""
        return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"

    # RAG Configuration
    rag_top_k: int = 3  # Number of documents to retrieve
    rag_batch_concurrency: int = 1  # Concurrent summarization requests (reduced for rate limit)
    rag_similarity_threshold: float = 0.6  # Minimum similarity score for relevant documents (0.0-1.0)
    rag_enable_authorization_check: bool = True  # Enable double-check for authorization rejections

    # Redis Configuration (for persistent docstore)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # Rate limiter storage configuration (shared backend)
    rate_limit_storage_uri: Optional[str] = None
    rate_limit_storage_db: int = 1

    # Chat Memory Configuration
    chat_history_ttl: int = 7200  # 2 hours in seconds
    chat_max_messages: int = 10  # Keep last 10 messages per session

    # PostgreSQL Configuration
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/chatbot_db"

    # JWT Authentication Configuration
    jwt_secret_key: str  # Generate with: openssl rand -hex 32
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # CORS Configuration
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    cors_allow_credentials: bool = True

    # Rate Limiting Configuration
    rate_limit_login: str = "5/minute"
    rate_limit_register: str = "3/hour"
    rate_limit_query: str = "20/minute"
    rate_limit_upload: str = "5/hour"
    rate_limit_api_key_create: str = "10/hour"
    rate_limit_api_key_list: str = "30/minute"
    rate_limit_api_key_delete: str = "10/minute"
    rate_limit_chat_history: str = "30/minute"
    rate_limit_default: str = "100/minute"

    # API Documentation Configuration
    enable_docs: bool = True
    enable_redoc: bool = True

    # Server Configuration
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    server_reload: bool = True
    server_log_level: str = "info"

    # LangSmith (Optional)
    langchain_api_key: Optional[str] = None
    langchain_tracing_v2: bool = False
    langchain_project: Optional[str] = None

    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    def get_rate_limit_storage_uri(self) -> str:
        """
        Build storage URI for the rate limiter.

        Returns:
            Storage URI string with credentials when required.
        """
        if self.rate_limit_storage_uri:
            return self.rate_limit_storage_uri

        return self._build_redis_uri(
            host=self.redis_host,
            port=self.redis_port,
            db=self.rate_limit_storage_db,
            password=self.redis_password,
        )

    def get_rate_limit_storage_display_uri(self) -> str:
        """
        Sanitized storage URI for logging/health endpoints.

        Returns:
            Storage URI without credentials to avoid leaking secrets.
        """
        uri = self.get_rate_limit_storage_uri()
        parsed = urlsplit(uri)

        if parsed.password or parsed.username:
            host = parsed.hostname or ""
            if parsed.port:
                host = f"{host}:{parsed.port}"
            return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))

        return uri

    @staticmethod
    def _build_redis_uri(host: str, port: int, db: int, password: Optional[str]) -> str:
        auth = ""
        if password:
            auth = f":{quote_plus(password)}@"
        return f"redis://{auth}{host}:{port}/{db}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()

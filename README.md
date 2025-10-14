<div align="center">

# 🤖 Chatbot-itsupport RAG API

**Production-ready FastAPI application for intelligent document processing and question answering**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com)
[![Pinecone](https://img.shields.io/badge/Pinecone-000000?style=for-the-badge&logo=pinecone&logoColor=white)](https://pinecone.io)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![LangChain](https://img.shields.io/badge/LangChain-121212?style=for-the-badge&logo=chainlink&logoColor=white)](https://langchain.com)

</div>

---

## ✨ Features

- 📄 **Multi-modal PDF Processing** - Extract text, tables, and images
- 🖼️ **Image Format Conversion** - Auto-convert to OpenAI-supported formats (PNG/JPEG)
- 🧠 **GPT-4o-mini Integration** - Intelligent summarization and Q&A
- 🔍 **Vector Search** - Pinecone-powered semantic retrieval
- 💾 **Redis Persistence** - Document storage and chat history
- 🎯 **RAG Pipeline** - Context-aware question answering
- 🔐 **JWT Authentication** - Secure user registration and login
- 🔑 **API Key Management** - Per-user API key authentication
- 💬 **Chat History** - Conversation context tracking
- ☁️ **Cloudflare R2 Storage** - Scalable PDF file storage
- 🛡️ **Rate Limiting** - SlowAPI protection per endpoint
- 🧹 **Auto Cleanup** - Background scheduler for old files
- 🎯 **Intent Detection** - Smart query classification
- ⚡ **Type-Safe** - Full type hints with Pydantic validation

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 15+ (user management database)
- Redis server (document store + chat history)
- OpenAI API key
- Pinecone API key
- Cloudflare R2 account (optional, for file storage)

**System Dependencies:**
```bash
# Ubuntu/Debian
sudo apt install poppler-utils tesseract-ocr ghostscript libmagic-dev

# macOS
brew install poppler tesseract libmagic
```

### Installation

```bash
# Clone repository
git clone https://github.com/your-repo/vectorize-api.git
cd vectorize-api

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Setup NLTK data (required for PDF processing)
./scripts/setup_nltk.sh

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run database migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

**API Documentation**: http://localhost:8000/docs

## 📡 API Usage

### 1. Register User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "myuser",
    "password": "SecurePass123!"
  }'
```

### 2. Login (Get JWT Token)

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=SecurePass123!"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Create API Key (Using JWT)

```bash
curl -X POST "http://localhost:8000/api/v1/api-keys" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Key",
    "expires_in_days": 365
  }'
```

### 4. Upload Document (Using API Key)

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@document.pdf"
```

**Response:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "file_size": 1048576,
  "num_chunks": 15,
  "num_tables": 3,
  "num_images": 5,
  "message": "Document uploaded and processed successfully"
}
```

### 5. Query Documents (RAG)

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the main topic of the document?",
    "top_k": 4
  }'
```

**Response:**
```json
{
  "answer": "Dokumen ini membahas tentang implementasi RAG...",
  "sources": ["doc1.pdf", "doc2.pdf"],
  "context": {
    "num_texts": 3,
    "num_images": 1
  }
}
```

### 6. Chat with History

```bash
curl -X POST "http://localhost:8000/api/v1/chat/query" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Jelaskan lebih detail",
    "session_id": "user-session-123",
    "top_k": 4
  }'
```

## ⚙️ Configuration

Key environment variables:

### Core Services

| Variable              | Description                | Default          |
| --------------------- | -------------------------- | ---------------- |
| `OPENAI_API_KEY`      | OpenAI API key             | Required         |
| `OPENAI_MODEL`        | Model name                 | `gpt-4o-mini`    |
| `PINECONE_API_KEY`    | Pinecone API key           | Required         |
| `PINECONE_INDEX_NAME` | Pinecone index name        | `multimodal-rag` |
| `DATABASE_URL`        | PostgreSQL connection URL  | Required         |
| `JWT_SECRET_KEY`      | JWT signing key            | Required         |

### Storage & Cache

| Variable                | Description                | Default     |
| ----------------------- | -------------------------- | ----------- |
| `REDIS_HOST`            | Redis host                 | `localhost` |
| `REDIS_PORT`            | Redis port                 | `6379`      |
| `REDIS_DB`              | Redis database number      | `0`         |
| `R2_ACCOUNT_ID`         | Cloudflare R2 account ID   | Optional    |
| `R2_ACCESS_KEY_ID`      | R2 access key              | Optional    |
| `R2_SECRET_ACCESS_KEY`  | R2 secret key              | Optional    |
| `R2_BUCKET_NAME`        | R2 bucket name             | Optional    |

### RAG & Processing

| Variable              | Description                   | Default |
| --------------------- | ----------------------------- | ------- |
| `RAG_TOP_K`           | Documents to retrieve         | `4`     |
| `PDF_MAX_FILE_SIZE`   | Max upload size (bytes)       | `10MB`  |
| `OCR_LANGUAGES`       | Tesseract languages (eng+ind) | `eng`   |
| `CHAT_HISTORY_TTL`    | Chat history TTL (seconds)    | `7200`  |

### Rate Limiting

| Variable                   | Description            | Default       |
| -------------------------- | ---------------------- | ------------- |
| `RATE_LIMIT_LOGIN`         | Login rate limit       | `5/minute`    |
| `RATE_LIMIT_REGISTER`      | Register rate limit    | `3/hour`      |
| `RATE_LIMIT_QUERY`         | Query rate limit       | `20/minute`   |
| `RATE_LIMIT_UPLOAD`        | Upload rate limit      | `5/hour`      |
| `RATE_LIMIT_API_KEY_CREATE`| API key creation limit | `10/hour`     |

See [`.env.example`](.env.example) for all options.

## 🏗️ Architecture

```
app/
├── api/routes/                  # API endpoints
│   ├── auth.py                  # JWT authentication (register/login)
│   ├── api_keys.py              # API key management (CRUD)
│   ├── document.py              # Document upload/delete
│   ├── query.py                 # RAG query endpoint
│   ├── chat.py                  # Chat with history
│   └── health.py                # Health checks
├── services/                    # Business logic
│   ├── pdf_processor.py         # PDF extraction + image conversion
│   ├── summarizer.py            # Content summarization
│   ├── vectorstore.py           # Pinecone vector operations
│   ├── redis_store.py           # Redis document store
│   ├── rag_chain.py             # RAG pipeline (LangChain)
│   ├── r2_storage.py            # Cloudflare R2 storage
│   ├── chat_memory.py           # Chat history management
│   ├── auth.py                  # Authentication service
│   ├── api_key.py               # API key service
│   ├── user.py                  # User management
│   └── cleanup_scheduler.py    # Background cleanup jobs
├── db/                          # Database layer
│   ├── database.py              # SQLAlchemy async setup
│   └── models.py                # User & APIKey ORM models
├── utils/                       # Utilities
│   ├── intent.py                # Query intent detection
│   └── strings.py               # String helper functions
├── models/                      # Pydantic schemas
│   ├── schemas.py               # API request/response models
│   └── documents.py             # Document models
├── core/                        # Configuration & security
│   ├── config.py                # Settings (Pydantic)
│   ├── security.py              # Password hashing, JWT
│   ├── dependencies.py          # FastAPI dependencies
│   ├── exceptions.py            # Custom exceptions
│   └── rate_limit.py            # Rate limiting config
└── main.py                      # FastAPI app entry point
```

### Data Flow

```
User Request
    ↓
[Authentication Layer] (JWT or API Key)
    ↓
[Rate Limiter] (SlowAPI)
    ↓
[API Routes] (FastAPI)
    ↓
[Services Layer]
    ├── PDFProcessor → Unstructured → PIL (image conversion)
    ├── Summarizer → OpenAI GPT-4o-mini
    ├── VectorStore → Pinecone (embeddings)
    ├── RedisStore → Redis (documents + chat)
    ├── R2Storage → Cloudflare R2 (files)
    └── RAGChain → LangChain → OpenAI
    ↓
[Database Layer]
    ├── PostgreSQL (users, api_keys)
    └── Redis (docstore, chat history)
    ↓
Response
```

## 🛠️ Tech Stack

<div align="center">

| Layer                | Technology                     |
| -------------------- | ------------------------------ |
| **Framework**        | FastAPI + Uvicorn              |
| **LLM**              | GPT-4o-mini (OpenAI)           |
| **Vector DB**        | Pinecone                       |
| **Database**         | PostgreSQL 15+ (async)         |
| **Cache/Store**      | Redis (docstore + chat)        |
| **File Storage**     | Cloudflare R2 (S3-compatible)  |
| **Embeddings**       | text-embedding-3-large (OpenAI)|
| **RAG Framework**    | LangChain                      |
| **PDF Processing**   | Unstructured + Tesseract OCR   |
| **Image Processing** | Pillow (PIL)                   |
| **Authentication**   | JWT (python-jose) + API Keys   |
| **Rate Limiting**    | SlowAPI                        |
| **Background Jobs**  | APScheduler                    |
| **ORM**              | SQLAlchemy 2.0 (async)         |
| **Migrations**       | Alembic                        |

</div>

## 📝 Development

### System Dependencies

**Ubuntu/Debian:**

```bash
sudo apt install poppler-utils tesseract-ocr ghostscript libmagic-dev redis-server postgresql
```

**macOS:**

```bash
brew install poppler tesseract libmagic redis postgresql
```

### Running Tests

```bash
# Unit tests
pytest tests/unit_tests/ -v

# Integration tests (requires Redis + PostgreSQL)
pytest tests/integration_tests/ -v

# Coverage report
pytest --cov=app --cov-report=html
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

## 🔒 Production Deployment

### 1. Environment Setup

```bash
# Generate secure JWT secret
openssl rand -hex 32

# Set all required environment variables in .env
# Never use development credentials in production!
```

### 2. Database Setup

```bash
# Create PostgreSQL database
createdb chatbot_db

# Run migrations
alembic upgrade head

# Verify connection
psql -d chatbot_db -c "\dt"
```

### 3. Redis Configuration

Enable persistence for production:

```bash
# /etc/redis/redis.conf
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfilename "appendonly.aof"
```

### 4. NLTK Data Setup

```bash
# Required for PDF processing
./scripts/setup_nltk.sh
```

### 5. Deployment Options

**Option A: Supervisor (Recommended for aaPanel)**

```ini
# /etc/supervisor/conf.d/vectorize-api.conf
[program:vectorize-api]
directory=/www/wwwroot/vectorize-api
command=/www/wwwroot/vectorize-api/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
user=www-data
autostart=true
autorestart=true
environment=PATH="/www/wwwroot/vectorize-api/venv/bin",NLTK_DATA="/www/wwwroot/vectorize-api/nltk_data"
stdout_logfile=/var/log/vectorize-api/access.log
stderr_logfile=/var/log/vectorize-api/error.log
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start vectorize-api
```

**Option B: Systemd**

```bash
# Use provided systemd/chatbot-itsupport.service
sudo cp systemd/chatbot-itsupport.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable chatbot-itsupport
sudo systemctl start chatbot-itsupport
```

**Option C: Docker (Future)**

```bash
# Coming soon...
docker-compose up -d
```

### 6. Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase timeout for large PDF uploads
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}
```

### 7. Monitoring & Logs

```bash
# Check service status
sudo supervisorctl status vectorize-api

# View logs
tail -f /var/log/vectorize-api/error.log

# Monitor Redis
redis-cli MONITOR

# Check PostgreSQL connections
psql -d chatbot_db -c "SELECT * FROM pg_stat_activity;"
```

### Security Checklist

- [ ] Change all default credentials
- [ ] Use strong JWT_SECRET_KEY (32+ characters)
- [ ] Enable HTTPS/SSL in production
- [ ] Configure CORS origins properly
- [ ] Set appropriate rate limits
- [ ] Enable Redis password authentication
- [ ] Use PostgreSQL role-based access
- [ ] Never commit `.env` to version control
- [ ] Regularly update dependencies
- [ ] Enable firewall (ufw/iptables)

## 🔐 Authentication Flow

The API supports two authentication methods:

### 1. JWT Token Authentication

For interactive users (web/mobile apps):

```
1. Register → POST /api/v1/auth/register
2. Login → POST /api/v1/auth/login (get JWT token)
3. Use token → Authorization: Bearer <token>
```

**Token expires in 30 minutes** (configurable via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`)

### 2. API Key Authentication

For programmatic access (scripts, integrations):

```
1. Login with JWT → Get access token
2. Create API key → POST /api/v1/api-keys (using JWT)
3. Use API key → X-API-Key: <api_key>
```

**API keys can have custom expiration dates** (default 365 days)

## 💬 Chat History

Conversation context is automatically managed using Redis:

- **Session-based**: Use `session_id` to maintain conversation context
- **TTL**: Chat history expires after 2 hours (configurable via `CHAT_HISTORY_TTL`)
- **Storage**: Last 10 messages kept per session (configurable via `CHAT_MAX_MESSAGES`)

```bash
# Start new conversation
curl -X POST "/api/v1/chat/query" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{"question": "Hello", "session_id": "user-123"}'

# Continue conversation (remembers context)
curl -X POST "/api/v1/chat/query" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{"question": "Tell me more", "session_id": "user-123"}'
```

## 🛡️ Rate Limiting

Default rate limits per endpoint:

- **Login**: 5 requests/minute
- **Register**: 3 requests/hour
- **Query**: 20 requests/minute
- **Upload**: 5 requests/hour
- **API Key Create**: 10 requests/hour

Rate limits are **per IP address** and enforced using SlowAPI with Redis backend.

## 🖼️ Image Format Support

The API automatically converts unsupported image formats to OpenAI-compatible formats:

**Supported Formats** (no conversion needed):
- PNG, JPEG, GIF, WebP

**Unsupported Formats** (auto-converted):
- TIFF → JPEG/PNG
- BMP → JPEG/PNG
- Other formats → JPEG/PNG (depending on transparency)

**Conversion Logic:**
- Images with transparency (RGBA, LA, P) → PNG
- RGB images → JPEG (quality 95%)
- Corrupt images → skipped with warning

## 📚 References

- [LangChain Docs](https://python.langchain.com/)
- [Pinecone Docs](https://docs.pinecone.io/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [OpenAI API](https://platform.openai.com/docs/)
- [Unstructured Docs](https://unstructured-io.github.io/unstructured/)
- [Cloudflare R2 Docs](https://developers.cloudflare.com/r2/)

## 📄 API Documentation

Detailed endpoint documentation available at:
- **Interactive Docs**: `/docs` (Swagger UI)
- **Alternative Docs**: `/redoc` (ReDoc)
- **Markdown Docs**: [`docs/api/`](docs/api/)

---

<div align="center">

**Built with ❤️ using FastAPI, OpenAI, Pinecone, PostgreSQL, Redis & LangChain**

</div>

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
- 🧠 **GPT-4o-mini Integration** - Intelligent summarization and Q&A
- 🔍 **Vector Search** - Pinecone-powered semantic retrieval
- 💾 **Redis Persistence** - Document storage across restarts
- 🎯 **RAG Pipeline** - Context-aware question answering
- ⚡ **Type-Safe** - Full type hints with Pydantic validation

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Redis server
- OpenAI API key
- Pinecone API key

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run server
uvicorn app.main:app --reload
```

**API Documentation**: http://localhost:8000/docs

## 📡 API Usage

### Upload Document

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@document.pdf"
```

### Query Documents

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the main topic?",
    "top_k": 4
  }'
```

## ⚙️ Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `OPENAI_MODEL` | Model name | `gpt-4o-mini` |
| `PINECONE_API_KEY` | Pinecone API key | Required |
| `PINECONE_INDEX_NAME` | Index name | `multimodal-rag` |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `RAG_TOP_K` | Retrieval count | `4` |

See [`.env.example`](.env.example) for all options.

## 🏗️ Architecture

```
app/
├── api/routes/      # API endpoints
├── services/        # Business logic
│   ├── pdf_processor.py
│   ├── summarizer.py
│   ├── vectorstore.py
│   ├── redis_store.py
│   └── rag_chain.py
├── models/          # Pydantic schemas
└── core/            # Configuration
```

## 🛠️ Tech Stack

<div align="center">

| Layer | Technology |
|-------|-----------|
| **Framework** | FastAPI |
| **LLM** | GPT-4o-mini (OpenAI) |
| **Vector DB** | Pinecone |
| **Document Store** | Redis |
| **Embeddings** | text-embedding-3-large |
| **RAG Framework** | LangChain |
| **PDF Processing** | Unstructured |

</div>

## 📝 Development

### System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils tesseract-ocr libmagic-dev redis-server
```

**macOS:**
```bash
brew install poppler tesseract libmagic redis
```

### Running Tests

```bash
pytest tests/
```

## 🔒 Production Deployment

### Redis Persistence

Enable Redis persistence for production:

```bash
# /etc/redis/redis.conf
save 900 1
save 300 10
save 60 10000
appendonly yes
```

### Production Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📚 References

- [LangChain Docs](https://python.langchain.com/)
- [Pinecone Docs](https://docs.pinecone.io/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [OpenAI API](https://platform.openai.com/docs/)

---

<div align="center">

**Built with ❤️ using FastAPI, OpenAI, Pinecone, Redis & LangChain**

</div>

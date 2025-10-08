<div align="center">

# 💬 Query Documents (RAG)

**Ask questions about indexed documents using Retrieval-Augmented Generation**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pinecone](https://img.shields.io/badge/Pinecone-000000?style=flat-square&logo=pinecone&logoColor=white)](https://pinecone.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white)](https://openai.com)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![LangChain](https://img.shields.io/badge/LangChain-121212?style=flat-square&logo=chainlink&logoColor=white)](https://langchain.com)

</div>

---

## 📋 Overview

Query endpoint allows users to ask questions about indexed documents. Uses **Retrieval-Augmented Generation (RAG)** to find relevant information and generate intelligent answers.

**🔓 Authentication:** Optional (supports JWT, API Key, or Anonymous)

### Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/query` | Ask questions about documents |

---

## Query Documents

### `POST /api/v1/query`

Ask a question and get an AI-generated answer based on indexed documents.

### 🔐 Authentication Methods

**1. JWT Token (All Users)**
```
Authorization: Bearer <jwt_token>
```

**2. API Key (Programmatic Access)**
```
X-API-Key: sk-proj-xxxxxxxxxxxxx
```

**3. Anonymous (No Authentication)**
- No header required
- Limited to public data only

### 📊 Role-Based Data Access

| Role | Access Level | Metadata Filter |
|------|--------------|-----------------|
| **Admin** | All data | None (no filtering) |
| **Lecturer** | Public + Internal | `{"sensitivity": {"$in": ["public", "internal"]}}` |
| **Student** | Public only | `{"sensitivity": "public"}` |
| **Anonymous** | Public only | `{"sensitivity": "public"}` |

### Request

**Headers:**
```
# Option 1: JWT Token
Authorization: Bearer <jwt_token>

# Option 2: API Key
X-API-Key: sk-proj-xxxxxxxxxxxxx

# Option 3: Anonymous (no header)
Content-Type: application/json
```

**Body:**
```json
{
  "question": "What is Retrieval-Augmented Generation?",
  "session_id": "user_session_123",
  "include_sources": true,
  "top_k": 4
}
```

**Fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `question` | string | ✅ Yes | - | Your question (min 1 char) |
| `session_id` | string | ❌ No | Auto-generated | Session ID for conversation history |
| `include_sources` | boolean | ❌ No | `false` | Include source documents in response |
| `top_k` | integer | ❌ No | `4` | Number of documents to retrieve (1-20) |

### Response

**Success Without Sources (200 OK):**
```json
{
  "answer": "Retrieval-Augmented Generation (RAG) is a technique that combines information retrieval with text generation. It retrieves relevant documents from a knowledge base and uses them to generate contextually accurate answers to questions.",
  "session_id": "user_session_123",
  "metadata": {
    "num_documents_retrieved": 4,
    "has_chat_history": false,
    "model": "gpt-4o-mini",
    "total_tokens": 456
  }
}
```

**Success With Sources (200 OK):**
```json
{
  "answer": "Retrieval-Augmented Generation (RAG) is a technique...",
  "session_id": "user_session_123",
  "sources": {
    "documents": [
      {
        "content": "RAG combines retrieval and generation...",
        "metadata": {
          "document_id": "123e4567-e89b-12d3-a456-426614174000",
          "content_type": "text",
          "sensitivity": "public",
          "source_link": "https://university.edu/courses/ai101/rag.pdf"
        }
      }
    ],
    "total_sources": 4
  },
  "metadata": {
    "num_documents_retrieved": 4,
    "has_chat_history": false,
    "model": "gpt-4o-mini"
  }
}
```

**No Results Found (200 OK):**
```json
{
  "answer": "I couldn't find any relevant information to answer your question.",
  "session_id": "user_session_123",
  "metadata": {
    "num_documents_retrieved": 0,
    "include_sources": false,
    "has_chat_history": false
  }
}
```

**Error (500 Internal Server Error):**
```json
{
  "detail": "Query processing failed: OpenAI API rate limit exceeded"
}
```

---

## Postman Testing

### Anonymous Query (Public Data)

**Step 1:** Create new POST request
```
POST http://localhost:8000/api/v1/query
```

**Step 2:** Set headers
```
Content-Type: application/json
```

**Step 3:** Add request body
```json
{
  "question": "What is machine learning?",
  "include_sources": true
}
```

**Step 4:** Send request

---

### Authenticated Query (JWT)

**Step 1:** Create new POST request
```
POST http://localhost:8000/api/v1/query
```

**Step 2:** Set Authorization
- Authorization tab → Type: Bearer Token
- Token: `{{jwt_token}}`

**Step 3:** Set headers
```
Content-Type: application/json
```

**Step 4:** Add request body
```json
{
  "question": "Explain neural networks",
  "session_id": "my_session_001",
  "include_sources": true,
  "top_k": 6
}
```

**Step 5:** Send request

---

### API Key Query

**Step 1:** Create new POST request
```
POST http://localhost:8000/api/v1/query
```

**Step 2:** Set headers
```
X-API-Key: sk-proj-xxxxxxxxxxxxx
Content-Type: application/json
```

**Step 3:** Add request body
```json
{
  "question": "What are the benefits of RAG?",
  "include_sources": false
}
```

**Step 4:** Send request

---

### Conversation with History

**Request 1:**
```json
{
  "question": "What is Python?",
  "session_id": "conversation_001"
}
```

**Request 2 (Same Session):**
```json
{
  "question": "What are its main features?",
  "session_id": "conversation_001"
}
```

The system remembers "its" refers to Python from previous question.

---

## cURL Examples

### Anonymous Query
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is machine learning?",
    "include_sources": true
  }'
```

### JWT Authentication
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Explain deep learning",
    "session_id": "my_session",
    "top_k": 5
  }'
```

### API Key Authentication
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "X-API-Key: sk-proj-xxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is supervised learning?",
    "include_sources": true
  }'
```

---

## 🔄 RAG Pipeline Flow

```
┌─────────────────┐
│  User Question  │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  Embedding          │
│  (text-embedding-   │
│   3-large)          │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Vector Search      │
│  (Pinecone)         │
│  + Metadata Filter  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Retrieve Original  │
│  Content (Redis)    │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Load Chat History  │
│  (Redis)            │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Generate Answer    │
│  (GPT-4o-mini +     │
│   Context)          │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Save to History    │
│  (Redis, 2hr TTL)   │
└────────┬────────────┘
         │
         ▼
┌─────────────────┐
│  Return Answer  │
└─────────────────┘
```

---

## 💡 Tips & Best Practices

### 1. Session Management

**Good Practice:**
```json
// Use consistent session_id for conversations
{
  "question": "What is Python?",
  "session_id": "user_123_chat"
}

// Follow-up question
{
  "question": "What are its advantages?",
  "session_id": "user_123_chat"  // Same session
}
```

**Bad Practice:**
```json
// Different session_id each time (loses context)
{
  "question": "What is Python?",
  "session_id": "session_1"
}

{
  "question": "What are its advantages?",
  "session_id": "session_2"  // Lost context!
}
```

### 2. Optimal top_k Values

| Use Case | Recommended top_k |
|----------|------------------|
| Quick facts | 2-3 |
| General questions | 4-6 (default: 4) |
| Complex topics | 8-10 |
| Comprehensive research | 15-20 |

### 3. Question Formulation

**✅ Good Questions:**
- "What is Retrieval-Augmented Generation?"
- "Explain the difference between supervised and unsupervised learning"
- "How does the transformer architecture work?"

**❌ Poor Questions:**
- "rag" (too short, ambiguous)
- "tell me everything" (too broad)
- "yes" (requires conversation context)

### 4. Including Sources

```json
// Development/Testing - include sources
{
  "question": "What is RAG?",
  "include_sources": true  // See what documents were used
}

// Production - exclude sources for faster response
{
  "question": "What is RAG?",
  "include_sources": false
}
```

---

## 🛠️ Common Errors

### 1. No Documents Found
```json
{
  "answer": "I couldn't find any relevant information to answer your question."
}
```
**Causes:**
- No documents uploaded yet
- Question doesn't match any indexed content
- User role doesn't have access to relevant documents

**Solutions:**
- Upload relevant documents first
- Rephrase question
- Check authentication/role permissions

### 2. OpenAI Rate Limit
```json
{
  "detail": "Query processing failed: OpenAI API rate limit exceeded"
}
```
**Solution:** Wait a few seconds and retry.

### 3. Invalid top_k Value
```json
{
  "detail": "top_k must be between 1 and 20"
}
```
**Solution:** Use value between 1-20.

### 4. Redis Connection Error
```json
{
  "detail": "Query processing failed: Redis connection refused"
}
```
**Solution:** Ensure Redis server is running.

---

## 📊 Performance Metrics

| Metric | Typical Value |
|--------|---------------|
| Response time | 2-5 seconds |
| Embedding time | 200-500ms |
| Vector search | 100-300ms |
| Answer generation | 1-3 seconds |
| Max conversation history | 10 messages (configurable) |
| Session TTL | 2 hours |
| Concurrent queries | Unlimited |

---

## 🔍 Testing Different Roles

### Anonymous (Public Only)
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is AI?"}'
```
**Expected:** Only retrieves documents with `sensitivity: "public"`

### Student (Public Only)
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Authorization: Bearer <student_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is AI?"}'
```
**Expected:** Only retrieves documents with `sensitivity: "public"`

### Lecturer (Public + Internal)
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Authorization: Bearer <lecturer_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is AI?"}'
```
**Expected:** Retrieves documents with `sensitivity: "public"` OR `"internal"`

### Admin (All Data)
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Authorization: Bearer <admin_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is AI?"}'
```
**Expected:** Retrieves ALL documents (no filtering)

---

## 📚 Related Documentation

- [← Previous: Document Upload](./03-documents.md)
- [Next: Chat History →](./05-chat-history.md)
- [How to get API Keys](./02-api-keys.md)
- [Understanding Roles](./01-authentication.md)

---

<div align="center">

**Built with** FastAPI • Pinecone • Redis • OpenAI • LangChain

[⬆️ Back to Top](#-query-documents-rag)

</div>

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
    "total_tokens": 456,
    "retrieved_documents": [
      {
        "document_id": "123e4567-e89b-12d3-a456-426614174000",
        "document_name": "rag_overview.pdf",
        "content_type": "text",
        "source_link": "https://university.edu/courses/ai101/rag.pdf",
        "similarity_score": 0.93
      }
    ],
    "similarity_scores": [0.93, 0.88, 0.85, 0.81],
    "max_similarity_score": 0.93,
    "min_similarity_score": 0.81,
    "avg_similarity_score": 0.8675,
    "source_links": [
      "https://university.edu/courses/ai101/rag.pdf"
    ]
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
          "source_link": "https://university.edu/courses/ai101/rag.pdf",
          "similarity_score": 0.93
        }
      }
    ],
    "total_sources": 4
  },
  "metadata": {
    "num_documents_retrieved": 4,
    "has_chat_history": false,
    "model": "gpt-4o-mini",
    "retrieved_documents": [
      {
        "document_id": "123e4567-e89b-12d3-a456-426614174000",
        "document_name": "rag_overview.pdf",
        "content_type": "text",
        "source_link": "https://university.edu/courses/ai101/rag.pdf",
        "similarity_score": 0.93
      }
    ],
    "similarity_scores": [0.93, 0.88, 0.85, 0.81],
    "max_similarity_score": 0.93,
    "min_similarity_score": 0.81,
    "avg_similarity_score": 0.8675,
    "source_links": [
      "https://university.edu/courses/ai101/rag.pdf"
    ]
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
    "has_chat_history": false,
    "retrieved_documents": [],
    "similarity_scores": []
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

## 🤖 Smart Source Handling

The API uses **intent detection** to intelligently decide when to include source links in answers.

### Small Talk Detection

The system recognizes small talk and won't append sources for simple greetings or acknowledgments:

**Detected as Small Talk:**
- **Greetings**: "hai", "halo", "hello", "hi", "selamat pagi/siang/sore/malam"
- **Thanks**: "terima kasih", "makasih", "thanks", "thank you"
- **Acknowledgments**: "oke", "ok", "sip", "siap", "noted"
- **Apologies**: "maaf", "sorry"

**Example:**
```json
// Request
{
  "question": "terima kasih atas penjelasannya"
}

// Response (no source links appended)
{
  "answer": "Sama-sama! Senang bisa membantu."
}
```

### Source Request Detection

When users explicitly ask for sources, the API automatically includes them inline:

**Source Keywords Detected:**
- Indonesian: "sumber", "referensi", "link", "tautan", "bukti", "dokumen", "lampiran"
- English: "source", "citation", "lihat dokumen"

**Example:**
```json
// Request
{
  "question": "Apa itu RAG? Berikan sumbernya",
  "include_sources": false  // Even if false, sources added due to keyword
}

// Response (sources appended inline)
{
  "answer": "RAG adalah Retrieval-Augmented Generation...\n\nSumber:\n- https://university.edu/rag.pdf\n- https://docs.openai.com/rag"
}
```

### Inline Source Format

When sources are included, they appear at the end of the answer in Indonesian format:

```
[Answer text here...]

Sumber:
- https://link1.com
- https://link2.com
- https://link3.com
```

**Conditions for Auto-Appending Sources:**
1. `include_sources: true` OR user asks for sources (keywords detected)
2. AND NOT small talk (greeting/thanks/acknowledgment)
3. AND documents were retrieved successfully

---

## 📊 Similarity Scores

Each retrieved document includes a **similarity score** (0.0 - 1.0) indicating relevance to the question.

### Score Interpretation

| Score Range | Relevance Level | Description |
|-------------|-----------------|-------------|
| **0.9 - 1.0** | Highly Relevant | Direct match, highly confident |
| **0.8 - 0.9** | Very Relevant | Strong semantic match |
| **0.7 - 0.8** | Relevant | Good match, useful information |
| **< 0.7** | Marginally Relevant | Weak match, may not be useful |

### Metadata Fields

**In every response metadata:**

```json
{
  "similarity_scores": [0.93, 0.88, 0.85, 0.81],
  "max_similarity_score": 0.93,
  "min_similarity_score": 0.81,
  "avg_similarity_score": 0.8675,
  "retrieved_documents": [
    {
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "document_name": "rag_guide.pdf",
      "content_type": "text",
      "source_link": "https://example.com/rag_guide.pdf",
      "similarity_score": 0.93
    }
  ],
  "source_links": [
    "https://example.com/rag_guide.pdf"
  ]
}
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `similarity_scores` | array | All similarity scores for retrieved documents |
| `max_similarity_score` | float | Highest similarity score |
| `min_similarity_score` | float | Lowest similarity score |
| `avg_similarity_score` | float | Average of all scores |
| `retrieved_documents` | array | Detailed metadata for each document |
| `source_links` | array | Unique source links (duplicates removed) |

### Using Scores for Quality Assessment

**High Quality Results (avg > 0.85):**
```json
{
  "avg_similarity_score": 0.89,
  "max_similarity_score": 0.95
}
```
✅ Answer is highly reliable, documents are very relevant

**Medium Quality Results (0.70 < avg < 0.85):**
```json
{
  "avg_similarity_score": 0.78,
  "max_similarity_score": 0.83
}
```
⚠️ Answer may be somewhat relevant, review sources

**Low Quality Results (avg < 0.70):**
```json
{
  "avg_similarity_score": 0.62,
  "max_similarity_score": 0.68
}
```
❌ Documents may not be very relevant, consider rephrasing question

---

## 🖼️ Image Format Support

The API automatically **converts images** extracted from PDFs to OpenAI Vision API-compatible formats.

### Supported Formats

**Native Support (No Conversion):**
- **PNG** - Portable Network Graphics
- **JPEG/JPG** - Joint Photographic Experts Group
- **GIF** - Graphics Interchange Format
- **WebP** - Web Picture format

**Auto-Converted Formats:**
- **TIFF** → JPEG or PNG
- **BMP** → JPEG or PNG
- **Other formats** → JPEG or PNG (depending on image properties)

### Conversion Rules

| Image Type | Conversion Target | Reason |
|------------|-------------------|---------|
| RGBA (transparency) | **PNG** | Preserves alpha channel |
| LA (grayscale + alpha) | **PNG** | Preserves transparency |
| P (palette mode) | **PNG** | Preserves color palette |
| RGB | **JPEG (quality 95%)** | Smaller file size |

### Handling Corrupt Images

If an image cannot be converted, it is **skipped with a warning** in the logs:

```
WARNING: Skipped 2 invalid or unsupported images
```

**Impact:**
- Query processing continues normally
- Other images are still used
- Answer is generated without corrupt images

**Example Log:**
```
INFO: Converting image from tiff to supported format
INFO: Successfully converted image to JPEG
WARNING: Skipping image: conversion to supported format failed
WARNING: Skipped 1 invalid or unsupported images
```

### Benefits

✅ **No user intervention needed** - Automatic format detection and conversion
✅ **Broad compatibility** - Works with most PDF image formats
✅ **Optimized quality** - JPEG quality 95% for minimal loss
✅ **Graceful degradation** - Skips corrupt images instead of failing

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
- "Apa saja komponen utama dalam RAG?" (specific question)
- "Bagaimana cara kerja vector search?" (how question)

**❌ Poor Questions:**
- "rag" (too short, ambiguous)
- "tell me everything" (too broad)
- "yes" (requires conversation context)
- "hai" (greeting, not a question)
- "oke" (acknowledgment, not a question)

### 4. Smart Question Formulation for Intent

**For Information Queries (Gets sources automatically):**
```json
{
  "question": "Apa itu machine learning? Berikan sumbernya"
}
// Auto-includes sources due to keyword "sumbernya"
```

**For Greetings/Small Talk (No sources needed):**
```json
{
  "question": "Terima kasih atas informasinya"
}
// No sources appended, recognized as small talk
```

**For Follow-up Questions:**
```json
{
  "question": "Jelaskan lebih detail tentang itu",
  "session_id": "same_session_id"  // Uses chat history for context
}
// Understands "itu" from previous conversation
```

### 5. Including Sources

**Explicit Control:**
```json
// Force include sources in response body
{
  "question": "What is RAG?",
  "include_sources": true
}

// Disable sources (but still auto-added if user asks for them)
{
  "question": "What is RAG?",
  "include_sources": false
}
```

**Automatic Behavior:**
- Sources **auto-appended inline** if question contains source keywords
- Small talk **never gets sources** appended
- Production: Use `false` for faster responses (unless sources explicitly needed)

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

### 5. Image Format Warning
```
WARNING: Skipped 2 invalid or unsupported images
```
**Cause:** Some images in PDF couldn't be converted to OpenAI-compatible format.

**Impact:**
- Query processing continues normally
- Answer generated without those images
- Other valid images still used

**Solutions:**
- Check PDF for corrupt/invalid images
- Verify image formats in source PDF
- This is a warning, not an error - system gracefully handles it

**Details:**
Images are automatically converted from formats like TIFF, BMP to PNG/JPEG. If conversion fails (corrupt data), the image is skipped but processing continues.

### 6. Low Similarity Scores
```json
{
  "avg_similarity_score": 0.58,
  "max_similarity_score": 0.65
}
```
**Cause:** Retrieved documents have low relevance to the question.

**Impact:** Answer may not be accurate or relevant.

**Solutions:**
- Rephrase question to be more specific
- Check if relevant documents are uploaded
- Try different keywords
- Increase `top_k` value to retrieve more documents

### 7. Small Talk Not Getting Response
**Issue:** User says "terima kasih" and expects detailed response.

**Cause:** Small talk detection recognized greeting/acknowledgment.

**Solution:**
- Small talk gets brief acknowledgment responses
- For information queries, use question words: "apa", "bagaimana", "jelaskan"
- Add context: "Terima kasih. Bisa jelaskan lebih lanjut tentang X?"

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

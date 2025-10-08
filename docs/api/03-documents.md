<div align="center">

# 📄 Document Upload

**Upload and process PDF documents for RAG**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pinecone](https://img.shields.io/badge/Pinecone-000000?style=flat-square&logo=pinecone&logoColor=white)](https://pinecone.io)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white)](https://openai.com)

</div>

---

## 📋 Overview

Document upload endpoint allows **Admin users** to upload PDF files for processing, summarization, and indexing in the vector database. Supports **single or batch upload** with custom metadata and sensitivity levels.

**⚠️ Admin authentication required**

### Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/documents/upload` | Upload single or multiple PDFs |

---

## Upload Document(s)

### `POST /api/v1/documents/upload`

Upload one or more PDF files for processing and indexing.

### Processing Pipeline

1. **Upload** → Save PDF file to disk
2. **Extract** → Extract text, tables, and images
3. **Summarize** → Generate summaries using GPT-4o-mini
4. **Index** → Store summaries in Pinecone vector DB
5. **Store** → Save original content in Redis

### Request

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
Content-Type: multipart/form-data
```

**Body (form-data):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files` | file(s) | ✅ Yes | One or more PDF files |
| `source_links` | string[] | ❌ No | Source URLs (must match file count) |
| `custom_metadata` | JSON string | ❌ No | Custom metadata (applies to all files) |

**Custom Metadata Example:**
```json
{
  "sensitivity": "public",
  "department": "Computer Science",
  "semester": "Fall 2025"
}
```

**Sensitivity Levels:**
- `public` - Accessible to everyone (anonymous, students, lecturers, admins)
- `internal` - Accessible to lecturers and admins only
- `confidential` - Accessible to admins only

### Response

**Single File Success (201 Created):**
```json
{
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "lecture-notes.pdf",
  "source_link": "https://university.edu/courses/cs101/notes.pdf",
  "custom_metadata": {
    "sensitivity": "public",
    "department": "Computer Science"
  },
  "status": "completed",
  "metadata": {
    "num_texts": 45,
    "num_tables": 3,
    "num_images": 7,
    "total_chunks": 55,
    "upload_timestamp": "2025-10-08T10:30:00"
  },
  "message": "Document processed and indexed successfully"
}
```

**Multiple Files Success (201 Created):**
```json
{
  "total_uploaded": 3,
  "successful": 2,
  "failed": 1,
  "results": [
    {
      "document_id": "123e4567-e89b-12d3-a456-426614174000",
      "filename": "lecture-1.pdf",
      "status": "completed",
      "metadata": {
        "num_texts": 30,
        "num_tables": 2,
        "num_images": 5,
        "total_chunks": 37
      },
      "message": "Document processed and indexed successfully"
    },
    {
      "document_id": "456e7890-e89b-12d3-a456-426614174001",
      "filename": "lecture-2.pdf",
      "status": "completed",
      "metadata": {
        "num_texts": 25,
        "num_tables": 1,
        "num_images": 3,
        "total_chunks": 29
      },
      "message": "Document processed and indexed successfully"
    },
    {
      "document_id": "",
      "filename": "corrupted.pdf",
      "status": "failed",
      "metadata": {
        "error": "Failed to process document: Invalid PDF file"
      },
      "message": "Failed to process: Invalid PDF file"
    }
  ],
  "message": "Processed 2 of 3 documents successfully"
}
```

**Error (403 Forbidden):**
```json
{
  "detail": "Access denied. Required role: admin"
}
```

**Error (400 Bad Request):**
```json
{
  "detail": "File lecture-notes.pdf: File size exceeds maximum allowed size of 10485760 bytes"
}
```

---

## Postman Testing

### Single File Upload

**Step 1:** Create new POST request
```
POST http://localhost:8000/api/v1/documents/upload
```

**Step 2:** Set Authorization
- Authorization tab → Type: Bearer Token
- Token: `{{jwt_token}}` (must be admin token)

**Step 3:** Set body type
- Body tab → Select `form-data`

**Step 4:** Add form fields

| Key | Type | Value |
|-----|------|-------|
| `files` | File | Select PDF file |
| `source_links` | Text | `https://example.com/doc.pdf` |
| `custom_metadata` | Text | `{"sensitivity": "public"}` |

**Step 5:** Send request

### Multiple Files Upload

**Step 1-3:** Same as single file

**Step 4:** Add multiple files

| Key | Type | Value |
|-----|------|-------|
| `files` | File | Select first PDF |
| `files` | File | Select second PDF |
| `files` | File | Select third PDF |
| `source_links` | Text | `https://example.com/doc1.pdf` |
| `source_links` | Text | `https://example.com/doc2.pdf` |
| `source_links` | Text | `https://example.com/doc3.pdf` |
| `custom_metadata` | Text | `{"sensitivity": "internal"}` |

**Note:** Click "+" next to `files` and `source_links` to add multiple values

**Step 5:** Send request

---

## cURL Examples

### Single File Upload

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer <admin_jwt_token>" \
  -F "files=@/path/to/document.pdf" \
  -F "source_links=https://university.edu/courses/doc.pdf" \
  -F 'custom_metadata={"sensitivity": "public", "department": "CS"}'
```

### Multiple Files Upload

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer <admin_jwt_token>" \
  -F "files=@/path/to/lecture-1.pdf" \
  -F "files=@/path/to/lecture-2.pdf" \
  -F "files=@/path/to/lecture-3.pdf" \
  -F "source_links=https://example.com/lecture-1.pdf" \
  -F "source_links=https://example.com/lecture-2.pdf" \
  -F "source_links=https://example.com/lecture-3.pdf" \
  -F 'custom_metadata={"sensitivity": "internal"}'
```

### Upload Without Optional Fields

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer <admin_jwt_token>" \
  -F "files=@/path/to/document.pdf"
```

---

## 📊 Processing Details

### What Gets Extracted?

1. **Text Chunks**
   - Chunked by title/section
   - Max 10,000 characters per chunk
   - Summarized with GPT-4o-mini

2. **Tables**
   - Extracted as structured data
   - Summarized descriptions

3. **Images**
   - Extracted as base64
   - AI-generated descriptions

### Storage Architecture

```
┌─────────────┐
│  PDF File   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Extract        │
│  (Text/Table/   │
│   Images)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Summarize      │
│  (GPT-4o-mini)  │
└────────┬────────┘
         │
         ├──────────────────────┐
         │                      │
         ▼                      ▼
┌─────────────────┐    ┌──────────────┐
│  Pinecone       │    │   Redis      │
│  (Summaries)    │    │  (Original)  │
└─────────────────┘    └──────────────┘
```

---

## 🛠️ Common Errors

### 1. Not Admin
```json
{
  "detail": "Access denied. Required role: admin"
}
```
**Solution:** Login with admin account.

### 2. File Too Large
```json
{
  "detail": "File size exceeds maximum allowed size of 10485760 bytes"
}
```
**Solution:** Reduce file size or split into multiple PDFs (max 10MB per file).

### 3. Invalid File Type
```json
{
  "detail": "File document.docx: Only PDF files are supported"
}
```
**Solution:** Convert to PDF format.

### 4. Source Links Mismatch
```json
{
  "detail": "Number of source_links (2) must match number of files (3)"
}
```
**Solution:** Provide same number of source_links as files, or omit source_links.

### 5. Invalid Metadata JSON
```json
{
  "detail": "Invalid JSON in custom_metadata: Expecting property name..."
}
```
**Solution:** Ensure custom_metadata is valid JSON string.

### 6. Reserved Metadata Keys
```json
{
  "detail": "Cannot use reserved keys in custom_metadata: {'doc_id', 'content_type'}"
}
```
**Solution:** Don't use these keys: `doc_id`, `document_id`, `content_type`, `source_link`.

---

## 💡 Best Practices

### 1. Sensitivity Levels

```json
// Public documents (accessible to all)
{"sensitivity": "public"}

// Internal documents (lecturers + admins)
{"sensitivity": "internal"}

// Confidential (admins only)
{"sensitivity": "confidential"}
```

### 2. Metadata Organization

```json
{
  "sensitivity": "internal",
  "department": "Computer Science",
  "course_code": "CS101",
  "semester": "Fall 2025",
  "topic": "Introduction to RAG"
}
```

### 3. File Naming

- ✅ Good: `cs101-lecture-01-introduction.pdf`
- ❌ Bad: `untitled.pdf`, `document (1).pdf`

### 4. Batch Upload Tips

- Upload related documents together (same course/topic)
- Use consistent metadata across batch
- Monitor response for failed files
- Re-upload failed files individually

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| Max file size | 10 MB |
| Supported format | PDF only |
| Processing time | ~30-60s per file |
| Concurrent uploads | Recommended: 1-3 files |
| Embedding model | text-embedding-3-large (3072 dim) |
| Summarization model | GPT-4o-mini |

---

## 🔍 Verification

After upload, verify document was indexed:

```bash
# Query to test
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What topics are covered in CS101?",
    "include_sources": true
  }'
```

Check response includes your uploaded document in sources.

---

## 📚 Related Documentation

- [← Previous: API Key Management](./02-api-keys.md)
- [Next: Query Documents →](./04-query.md)
- [Understanding Sensitivity Levels](./04-query.md#-role-based-data-access)

---

<div align="center">

**Built with** FastAPI • Pinecone • Redis • OpenAI • Unstructured

[⬆️ Back to Top](#-document-upload)

</div>

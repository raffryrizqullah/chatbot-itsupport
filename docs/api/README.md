<div align="center">

# 📚 API Documentation

**Complete API Reference for Chatbot IT Support RAG System**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![Pinecone](https://img.shields.io/badge/Pinecone-000000?style=flat-square&logo=pinecone&logoColor=white)](https://pinecone.io)
[![JWT](https://img.shields.io/badge/JWT-000000?style=flat-square&logo=jsonwebtokens&logoColor=white)](https://jwt.io)

</div>

---

## 🎯 Quick Start

### Base URL
```
http://localhost:8000
```

### Interactive API Docs
```
http://localhost:8000/docs       # Swagger UI
http://localhost:8000/redoc      # ReDoc
```

---

## 📖 Available Endpoints

### 1. [🔐 Authentication](./01-authentication.md)
Manage user authentication with JWT tokens.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/auth/register` | Register new user | ❌ No |
| `POST` | `/api/v1/auth/login` | Login and get JWT token | ❌ No |
| `GET` | `/api/v1/auth/me` | Get current user info | ✅ JWT |

[**📄 View Documentation →**](./01-authentication.md)

---

### 2. [🔑 API Key Management](./02-api-keys.md)
Admin-only endpoints for managing API keys.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/admin/api-keys` | Create API key for user | ✅ Admin |
| `GET` | `/api/v1/admin/api-keys` | List all API keys | ✅ Admin |
| `GET` | `/api/v1/admin/api-keys/{key_id}` | Get API key details | ✅ Admin |
| `DELETE` | `/api/v1/admin/api-keys/{key_id}` | Revoke API key | ✅ Admin |
| `GET` | `/api/v1/admin/users/{user_id}/api-keys` | List user's API keys | ✅ Admin |

[**📄 View Documentation →**](./02-api-keys.md)

---

### 3. [📄 Document Management](./03-documents.md)
Upload and process PDF documents.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/documents/upload` | Upload PDF document(s) | ✅ Admin |

[**📄 View Documentation →**](./03-documents.md)

---

### 4. [💬 Query (RAG)](./04-query.md)
Ask questions about indexed documents.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/query` | Query documents with RAG | ⚠️ Optional (JWT/API Key) |

[**📄 View Documentation →**](./04-query.md)

---

### 5. [🗨️ Chat History](./05-chat-history.md)
Manage conversation history.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/api/v1/history/{session_id}` | Get chat history | ❌ No |
| `GET` | `/api/v1/session/{session_id}` | Get session info | ❌ No |
| `DELETE` | `/api/v1/history/{session_id}` | Clear chat history | ❌ No |

[**📄 View Documentation →**](./05-chat-history.md)

---

### 6. [❤️ Health Check](./06-health.md)
Check API health status.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/health` | Get API health status | ❌ No |

[**📄 View Documentation →**](./06-health.md)

---

## 🔐 Authentication Methods

### 1. JWT Token (All Users)
```bash
Authorization: Bearer <your_jwt_token>
```

**How to get token:**
1. Login via `/api/v1/auth/login`
2. Copy `access_token` from response
3. Use in Authorization header

### 2. API Key (Programmatic Access)
```bash
X-API-Key: sk-proj-xxxxxxxxxxxxx
```

**How to get API key:**
1. Admin creates key via `/api/v1/admin/api-keys`
2. Copy full key (shown only once!)
3. Use in X-API-Key header

---

## 👥 User Roles & Permissions

### 🔴 Admin
- Full access to all endpoints
- Can upload documents
- Can create/manage API keys
- Can access all data (no filtering)

### 🟡 Lecturer
- Can query documents
- Access to **public** + **internal** data
- Cannot upload documents
- Cannot manage API keys

### 🟢 Student
- Can query documents
- Access to **public** data only
- Cannot upload documents
- Cannot manage API keys

### ⚪ Anonymous (No Auth)
- Can query documents
- Access to **public** data only
- Limited to public endpoints

---

## 🧪 Testing with Postman

### Step 1: Setup Environment
Create environment variables in Postman:

```
base_url = http://localhost:8000
jwt_token = (leave empty, will be set after login)
api_key = (leave empty, will be set after creation)
```

### Step 2: Authentication Flow
1. **Register** → `POST {{base_url}}/api/v1/auth/register`
2. **Login** → `POST {{base_url}}/api/v1/auth/login`
3. Save `access_token` to `{{jwt_token}}`
4. Use `Bearer {{jwt_token}}` in subsequent requests

### Step 3: Test Endpoints
Follow documentation for each endpoint:
- [Authentication](./01-authentication.md)
- [API Keys](./02-api-keys.md)
- [Documents](./03-documents.md)
- [Query](./04-query.md)
- [Chat History](./05-chat-history.md)

---

## 🛠️ Common Errors

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```
**Solution:** Include valid JWT token or API key in headers.

### 403 Forbidden
```json
{
  "detail": "Access denied. Required role: admin"
}
```
**Solution:** Use account with required role (check permissions table above).

### 500 Internal Server Error
```json
{
  "error": "InternalServerError",
  "message": "An unexpected error occurred"
}
```
**Solution:** Check server logs and ensure all services (Redis, PostgreSQL, Pinecone) are running.

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/chatbot-itsupport/issues)
- **Documentation:** `/docs` (Swagger UI)
- **API Version:** `1.0.0`

---

<div align="center">

**Built with** FastAPI • PostgreSQL • Redis • Pinecone • OpenAI • LangChain

[⬆️ Back to Top](#-api-documentation)

</div>

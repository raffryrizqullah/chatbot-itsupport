<div align="center">

# 🔑 API Key Management

**Admin-only endpoints for creating and managing API keys**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Bcrypt](https://img.shields.io/badge/Bcrypt-Security-red?style=flat-square)](https://bcrypt.online)

</div>

---

## 📋 Overview

API Keys provide programmatic access to the API without requiring repeated logins. Only **Admin users** can create and manage API keys for other users.

**⚠️ All endpoints require Admin authentication**

### Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/admin/api-keys` | Create new API key |
| `GET` | `/api/v1/admin/api-keys` | List all API keys |
| `GET` | `/api/v1/admin/api-keys/{key_id}` | Get API key details |
| `DELETE` | `/api/v1/admin/api-keys/{key_id}` | Revoke API key |
| `GET` | `/api/v1/admin/users/{user_id}/api-keys` | List user's API keys |

---

## 1. Create API Key

### `POST /api/v1/admin/api-keys`

Create a new API key for a user. **The full key is only shown once!**

### Request

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json
```

**Body:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Chatbot Application"
}
```

**Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string (UUID) | ✅ Yes | User ID who will own this key |
| `name` | string | ✅ Yes | Descriptive name for the API key |

### Response

**Success (201 Created):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "key_prefix": "sk-proj-abc...",
  "name": "My Chatbot Application",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "student1",
  "is_active": true,
  "created_at": "2025-10-08T10:30:00",
  "last_used_at": null,
  "api_key": "sk-proj-abc123def456ghi789jkl012mno345pqr678stu"
}
```

**⚠️ IMPORTANT:** Save the `api_key` value immediately! It won't be shown again.

**Error (403 Forbidden):**
```json
{
  "detail": "Access denied. Required role: admin"
}
```

### Postman Testing

**Step 1:** Create new POST request
```
POST http://localhost:8000/api/v1/admin/api-keys
```

**Step 2:** Set Authorization
- Authorization tab → Type: Bearer Token
- Token: `{{jwt_token}}` (must be admin token)

**Step 3:** Set headers
```
Content-Type: application/json
```

**Step 4:** Add request body
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Postman Testing Key"
}
```

**Step 5:** Send request

**Step 6:** **COPY AND SAVE THE `api_key` FROM RESPONSE!**

### cURL Example

```bash
curl -X POST "http://localhost:8000/api/v1/admin/api-keys" \
  -H "Authorization: Bearer <admin_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "My Chatbot Application"
  }'
```

---

## 2. List All API Keys

### `GET /api/v1/admin/api-keys`

List all API keys in the system (optionally filtered by user).

### Request

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string (UUID) | ❌ No | Filter by user ID |

### Response

**Success (200 OK):**
```json
{
  "total": 3,
  "api_keys": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "key_prefix": "sk-proj-abc...",
      "name": "Chatbot Web App",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "student1",
      "is_active": true,
      "created_at": "2025-10-08T10:30:00",
      "last_used_at": "2025-10-08T12:45:00"
    },
    {
      "id": "456e7890-e89b-12d3-a456-426614174001",
      "key_prefix": "sk-proj-def...",
      "name": "Mobile App",
      "user_id": "660e8400-e29b-41d4-a716-446655440001",
      "username": "lecturer1",
      "is_active": true,
      "created_at": "2025-10-07T14:20:00",
      "last_used_at": null
    }
  ]
}
```

### Postman Testing

**Step 1:** Create new GET request
```
GET http://localhost:8000/api/v1/admin/api-keys
```

**Step 2:** Set Authorization
- Authorization tab → Type: Bearer Token
- Token: `{{jwt_token}}` (admin token)

**Step 3 (Optional):** Filter by user
```
GET http://localhost:8000/api/v1/admin/api-keys?user_id=550e8400-e29b-41d4-a716-446655440000
```

**Step 4:** Send request

### cURL Example

```bash
# List all keys
curl -X GET "http://localhost:8000/api/v1/admin/api-keys" \
  -H "Authorization: Bearer <admin_jwt_token>"

# Filter by user
curl -X GET "http://localhost:8000/api/v1/admin/api-keys?user_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <admin_jwt_token>"
```

---

## 3. Get API Key Details

### `GET /api/v1/admin/api-keys/{key_id}`

Get detailed information about a specific API key.

### Request

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `key_id` | string (UUID) | ✅ Yes | API key ID |

### Response

**Success (200 OK):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "key_prefix": "sk-proj-abc...",
  "name": "My Chatbot Application",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "student1",
  "is_active": true,
  "created_at": "2025-10-08T10:30:00",
  "last_used_at": "2025-10-08T12:45:00"
}
```

**Error (404 Not Found):**
```json
{
  "detail": "API key 123e4567-e89b-12d3-a456-426614174000 not found"
}
```

### Postman Testing

**Step 1:** Create new GET request
```
GET http://localhost:8000/api/v1/admin/api-keys/123e4567-e89b-12d3-a456-426614174000
```

**Step 2:** Set Authorization
- Authorization tab → Type: Bearer Token
- Token: `{{jwt_token}}` (admin token)

**Step 3:** Send request

### cURL Example

```bash
curl -X GET "http://localhost:8000/api/v1/admin/api-keys/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer <admin_jwt_token>"
```

---

## 4. Revoke API Key

### `DELETE /api/v1/admin/api-keys/{key_id}`

Revoke (deactivate) an API key. Revoked keys cannot be used for authentication.

### Request

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `key_id` | string (UUID) | ✅ Yes | API key ID to revoke |

### Response

**Success (200 OK):**
```json
{
  "message": "API key 123e4567-e89b-12d3-a456-426614174000 revoked successfully",
  "success": true
}
```

**Error (404 Not Found):**
```json
{
  "detail": "API key 123e4567-e89b-12d3-a456-426614174000 not found"
}
```

### Postman Testing

**Step 1:** Create new DELETE request
```
DELETE http://localhost:8000/api/v1/admin/api-keys/123e4567-e89b-12d3-a456-426614174000
```

**Step 2:** Set Authorization
- Authorization tab → Type: Bearer Token
- Token: `{{jwt_token}}` (admin token)

**Step 3:** Send request

### cURL Example

```bash
curl -X DELETE "http://localhost:8000/api/v1/admin/api-keys/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer <admin_jwt_token>"
```

---

## 5. List User's API Keys

### `GET /api/v1/admin/users/{user_id}/api-keys`

List all API keys belonging to a specific user.

### Request

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string (UUID) | ✅ Yes | User ID |

### Response

**Success (200 OK):**
```json
{
  "total": 2,
  "api_keys": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "key_prefix": "sk-proj-abc...",
      "name": "Web App",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "student1",
      "is_active": true,
      "created_at": "2025-10-08T10:30:00",
      "last_used_at": "2025-10-08T12:45:00"
    },
    {
      "id": "456e7890-e89b-12d3-a456-426614174001",
      "key_prefix": "sk-proj-def...",
      "name": "Mobile App",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "student1",
      "is_active": false,
      "created_at": "2025-10-07T14:20:00",
      "last_used_at": null
    }
  ]
}
```

### Postman Testing

**Step 1:** Create new GET request
```
GET http://localhost:8000/api/v1/admin/users/550e8400-e29b-41d4-a716-446655440000/api-keys
```

**Step 2:** Set Authorization
- Authorization tab → Type: Bearer Token
- Token: `{{jwt_token}}` (admin token)

**Step 3:** Send request

### cURL Example

```bash
curl -X GET "http://localhost:8000/api/v1/admin/users/550e8400-e29b-41d4-a716-446655440000/api-keys" \
  -H "Authorization: Bearer <admin_jwt_token>"
```

---

## 🔐 Using API Keys for Authentication

Once you have an API key, you can use it instead of JWT token:

### Method 1: X-API-Key Header (Recommended)
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "X-API-Key: sk-proj-abc123def456ghi789jkl012mno345pqr678stu" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG?"}'
```

### Method 2: Authorization Header
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Authorization: Bearer sk-proj-abc123def456ghi789jkl012mno345pqr678stu" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG?"}'
```

---

## 🛠️ Common Errors

### 1. Not Admin
```json
{
  "detail": "Access denied. Required role: admin"
}
```
**Solution:** Login with an admin account.

### 2. User Not Found
```json
{
  "detail": "Failed to create API key: User <user_id> not found"
}
```
**Solution:** Verify the user_id exists (check via `/api/v1/auth/me` or database).

### 3. Invalid API Key
```json
{
  "detail": "Not authenticated"
}
```
**Solution:** Check the API key is correct and hasn't been revoked.

### 4. API Key Revoked
```json
{
  "detail": "Not authenticated"
}
```
**Solution:** Create a new API key.

---

## 💡 Best Practices

1. **Naming Convention** - Use descriptive names: "Production Web App", "Mobile iOS App"
2. **Key Rotation** - Revoke and regenerate keys periodically
3. **Least Privilege** - Create keys only for users who need programmatic access
4. **Secure Storage** - Store keys in environment variables, never in code
5. **Monitor Usage** - Check `last_used_at` to identify unused keys

---

## 📊 API Key Format

API keys follow the OpenAI/Claude format:
```
sk-proj-{43_random_characters}

Example: sk-proj-abc123def456ghi789jkl012mno345pqr678stu
```

- **Prefix**: `sk-proj-` (identifies as project API key)
- **Length**: 51 characters total
- **Hashed**: Keys are bcrypt-hashed before storage
- **Display**: Only first 12 chars shown in listings (``sk-proj-abc...``)

---

## 📚 Related Documentation

- [← Previous: Authentication](./01-authentication.md)
- [Next: Document Upload →](./03-documents.md)
- [How to use API Keys in Query](./04-query.md#-authentication-methods)

---

<div align="center">

**Built with** FastAPI • PostgreSQL • Bcrypt

[⬆️ Back to Top](#-api-key-management)

</div>

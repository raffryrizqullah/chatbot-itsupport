<div align="center">

# 🔐 Authentication Endpoints

**User authentication with JWT tokens**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![JWT](https://img.shields.io/badge/JWT-000000?style=flat-square&logo=jsonwebtokens&logoColor=white)](https://jwt.io)

</div>

---

## 📋 Overview

Authentication endpoints handle user registration, login, and profile retrieval using JWT (JSON Web Token) for secure session management.

### Available Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/auth/register` | Register new user | ❌ No |
| `POST` | `/api/v1/auth/login` | Login and get JWT token | ❌ No |
| `GET` | `/api/v1/auth/me` | Get current user info | ✅ JWT Token |

---

## 1. Register User

### `POST /api/v1/auth/register`

Create a new user account.

### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "username": "student1",
  "email": "student@university.edu",
  "password": "password123",
  "full_name": "Alice Student",
  "role": "student"
}
```

**Fields:**
| Field | Type | Required | Description | Allowed Values |
|-------|------|----------|-------------|----------------|
| `username` | string | ✅ Yes | Unique username (3-50 chars) | - |
| `email` | string | ✅ Yes | Valid email address | - |
| `password` | string | ✅ Yes | Password (min 6 chars) | - |
| `full_name` | string | ✅ Yes | User's full name | - |
| `role` | string | ❌ No | User role (default: student) | `admin`, `lecturer`, `student` |

### Response

**Success (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "student1",
    "email": "student@university.edu",
    "full_name": "Alice Student",
    "role": "student",
    "is_active": true,
    "created_at": "2025-10-08T10:30:00"
  }
}
```

**Error (400 Bad Request):**
```json
{
  "detail": "Username student1 already exists"
}
```

### Postman Testing

**Step 1:** Create new POST request
```
POST http://localhost:8000/api/v1/auth/register
```

**Step 2:** Set headers
```
Content-Type: application/json
```

**Step 3:** Add request body (Body → raw → JSON)
```json
{
  "username": "testuser",
  "email": "testuser@test.com",
  "password": "test123",
  "full_name": "Test User",
  "role": "student"
}
```

**Step 4:** Send request

**Step 5:** Save `access_token` from response
- Go to Environment variables
- Create/update variable: `jwt_token`
- Paste the token value

### cURL Example

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student1",
    "email": "student@university.edu",
    "password": "password123",
    "full_name": "Alice Student",
    "role": "student"
  }'
```

---

## 2. Login

### `POST /api/v1/auth/login`

Login with username and password to get JWT token.

### Request

**Headers:**
```
Content-Type: application/x-www-form-urlencoded
```

**Body (form-data):**
```
username: student1
password: password123
```

### Response

**Success (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "student1",
    "email": "student@university.edu",
    "full_name": "Alice Student",
    "role": "student",
    "is_active": true,
    "created_at": "2025-10-08T10:30:00"
  }
}
```

**Error (401 Unauthorized):**
```json
{
  "detail": "Incorrect username or password"
}
```

### Postman Testing

**Step 1:** Create new POST request
```
POST http://localhost:8000/api/v1/auth/login
```

**Step 2:** Select Body → x-www-form-urlencoded

**Step 3:** Add form data
```
username: student1
password: password123
```

**Step 4:** Send request

**Step 5:** Auto-save token (Optional)
- Go to Tests tab
- Add script:
```javascript
var jsonData = pm.response.json();
if (jsonData.access_token) {
    pm.environment.set("jwt_token", jsonData.access_token);
}
```

### cURL Example

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=student1&password=password123"
```

---

## 3. Get Current User

### `GET /api/v1/auth/me`

Get information about the currently authenticated user.

### Request

**Headers:**
```
Authorization: Bearer <your_jwt_token>
```

### Response

**Success (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "student1",
  "email": "student@university.edu",
  "full_name": "Alice Student",
  "role": "student",
  "is_active": true,
  "created_at": "2025-10-08T10:30:00"
}
```

**Error (401 Unauthorized):**
```json
{
  "detail": "Not authenticated"
}
```

### Postman Testing

**Step 1:** Create new GET request
```
GET http://localhost:8000/api/v1/auth/me
```

**Step 2:** Set Authorization
- Go to Authorization tab
- Type: Bearer Token
- Token: `{{jwt_token}}`

**Step 3:** Send request

### cURL Example

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## 🔄 Complete Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant DB

    Client->>API: POST /auth/register
    API->>DB: Create user
    DB-->>API: User created
    API-->>Client: JWT token + user info

    Client->>API: POST /auth/login
    API->>DB: Verify credentials
    DB-->>API: User found
    API-->>Client: JWT token + user info

    Client->>API: GET /auth/me (with JWT)
    API->>DB: Get user by ID from token
    DB-->>API: User details
    API-->>Client: User info
```

---

## 🛠️ Common Errors

### 1. Username Already Exists
```json
{
  "detail": "Username student1 already exists"
}
```
**Solution:** Choose a different username.

### 2. Email Already Exists
```json
{
  "detail": "Email student@university.edu already exists"
}
```
**Solution:** Use a different email or login instead.

### 3. Invalid Credentials
```json
{
  "detail": "Incorrect username or password"
}
```
**Solution:** Check username and password are correct.

### 4. Token Expired
```json
{
  "detail": "Invalid or expired token"
}
```
**Solution:** Login again to get a new token.

### 5. Inactive User
```json
{
  "detail": "Inactive user"
}
```
**Solution:** Contact admin to activate your account.

---

## 💡 Tips

1. **Save tokens securely** - Don't commit tokens to git
2. **Token expiration** - Default: 30 minutes (configurable)
3. **Password strength** - Minimum 6 characters required
4. **Role selection** - Contact admin to change role after registration

---

## 📚 Related Documentation

- [← Back to API Index](./README.md)
- [Next: API Key Management →](./02-api-keys.md)

---

<div align="center">

**Built with** FastAPI • PostgreSQL • JWT • Bcrypt

[⬆️ Back to Top](#-authentication-endpoints)

</div>

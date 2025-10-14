# 💬 Query Endpoint - Frontend Integration Guide

**Simple guide for implementing chat interface with RAG query endpoint**

---

## 🚀 Quick Start

### Endpoint

```
POST /api/v1/query
```

### Base URL
```
Production: https://api.yourdomain.com/api/v1/query
Development: http://localhost:8000/api/v1/query
```

### Authentication (Optional)

```typescript
// Option 1: JWT Token (for logged-in users)
headers: {
  'Authorization': 'Bearer YOUR_JWT_TOKEN',
  'Content-Type': 'application/json'
}

// Option 2: API Key (for programmatic access)
headers: {
  'X-API-Key': 'sk-proj-xxxxxxxxxxxxx',
  'Content-Type': 'application/json'
}

// Option 3: Anonymous (public data only)
headers: {
  'Content-Type': 'application/json'
}
```

---

## 📦 TypeScript Types

```typescript
// Request
interface QueryRequest {
  question: string;                // Required: User's question
  session_id?: string;             // Optional: For conversation context
  include_sources?: boolean;       // Optional: Default false
  top_k?: number;                  // Optional: 1-20, default 4
}

// Response
interface QueryResponse {
  answer: string;                  // AI-generated answer (may include inline sources)
  session_id: string;              // Session ID for this conversation
  metadata: {
    num_documents_retrieved: number;
    has_chat_history: boolean;
    model: string;
    similarity_scores?: number[];
    max_similarity_score?: number;
    avg_similarity_score?: number;
    retrieved_documents?: Array<{
      document_id: string;
      document_name: string;
      content_type: string;
      source_link: string;
      similarity_score: number;
    }>;
    source_links?: string[];       // Unique source URLs
  };
}

// Error Response
interface ErrorResponse {
  detail: string;
}
```

---

## 💻 Implementation Examples

### Basic Fetch Example

```typescript
async function sendQuery(question: string, sessionId?: string): Promise<QueryResponse> {
  const response = await fetch('/api/v1/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      // Add auth header if needed
      // 'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      question,
      session_id: sessionId,
      include_sources: false  // Sources auto-added if user asks
    })
  });

  if (!response.ok) {
    const error: ErrorResponse = await response.json();
    throw new Error(error.detail);
  }

  return response.json();
}
```

### Axios Example

```typescript
import axios from 'axios';

const queryAPI = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  }
});

// Add auth interceptor if needed
queryAPI.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

async function askQuestion(question: string, sessionId?: string): Promise<QueryResponse> {
  const { data } = await queryAPI.post<QueryResponse>('/query', {
    question,
    session_id: sessionId,
  });
  return data;
}
```

---

## 🎨 Chat Display Implementation

### State Management

```typescript
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: string[];  // Extracted from inline sources
  isLoading?: boolean;
}

interface ChatState {
  messages: ChatMessage[];
  sessionId: string;
  isLoading: boolean;
}

// Initialize state
const [chatState, setChatState] = useState<ChatState>({
  messages: [],
  sessionId: generateSessionId(), // user_123_chat
  isLoading: false,
});
```

### Send Message Function

```typescript
async function handleSendMessage(userQuestion: string) {
  // Add user message
  const userMsg: ChatMessage = {
    id: crypto.randomUUID(),
    role: 'user',
    content: userQuestion,
    timestamp: new Date(),
  };

  setChatState(prev => ({
    ...prev,
    messages: [...prev.messages, userMsg],
    isLoading: true,
  }));

  try {
    // Call API
    const response = await sendQuery(userQuestion, chatState.sessionId);

    // Extract sources from answer if present
    const sources = extractSourcesFromAnswer(response.answer);

    // Add assistant message
    const assistantMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: response.answer,
      timestamp: new Date(),
      sources: sources,
    };

    setChatState(prev => ({
      ...prev,
      messages: [...prev.messages, assistantMsg],
      isLoading: false,
    }));

  } catch (error) {
    // Handle error
    const errorMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: 'Maaf, terjadi kesalahan. Silakan coba lagi.',
      timestamp: new Date(),
    };

    setChatState(prev => ({
      ...prev,
      messages: [...prev.messages, errorMsg],
      isLoading: false,
    }));
  }
}
```

### Extract Inline Sources

```typescript
function extractSourcesFromAnswer(answer: string): string[] | undefined {
  // Check if answer contains "Sumber:" section
  const sourcesMatch = answer.match(/\n\nSumber:\n((?:- https?:\/\/[^\n]+\n?)+)/);

  if (!sourcesMatch) return undefined;

  // Extract URLs
  const sourceLines = sourcesMatch[1].trim().split('\n');
  const urls = sourceLines
    .map(line => line.replace(/^- /, '').trim())
    .filter(url => url.startsWith('http'));

  return urls.length > 0 ? urls : undefined;
}
```

---

## ✨ Smart Features

### 1. Session Management (Context Memory)

```typescript
// Keep same session_id for conversation
const SESSION_KEY = 'chat_session_id';

function getSessionId(): string {
  let sessionId = localStorage.getItem(SESSION_KEY);

  if (!sessionId) {
    sessionId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem(SESSION_KEY, sessionId);
  }

  return sessionId;
}

// Clear session to start fresh conversation
function resetSession() {
  localStorage.removeItem(SESSION_KEY);
  setChatState(prev => ({
    ...prev,
    messages: [],
    sessionId: getSessionId(),
  }));
}
```

### 2. Smart Source Display

```tsx
// Display message with clickable sources
function ChatMessage({ message }: { message: ChatMessage }) {
  // Remove sources from content for display
  const cleanContent = message.content.replace(/\n\nSumber:\n((?:- https?:\/\/[^\n]+\n?)+)/, '');

  return (
    <div className={`message ${message.role}`}>
      <div className="content">{cleanContent}</div>

      {message.sources && message.sources.length > 0 && (
        <div className="sources">
          <strong>Sumber:</strong>
          <ul>
            {message.sources.map((url, idx) => (
              <li key={idx}>
                <a href={url} target="_blank" rel="noopener noreferrer">
                  {url}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

### 3. Loading States

```tsx
function ChatInterface() {
  return (
    <div className="chat-container">
      {chatState.messages.map(msg => (
        <ChatMessage key={msg.id} message={msg} />
      ))}

      {chatState.isLoading && (
        <div className="loading">
          <span>Mencari dokumen...</span>
          <span className="dots">...</span>
        </div>
      )}
    </div>
  );
}
```

---

## 🛠️ Error Handling

```typescript
async function sendQueryWithErrorHandling(
  question: string,
  sessionId?: string
): Promise<QueryResponse> {
  try {
    const response = await fetch('/api/v1/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, session_id: sessionId }),
    });

    if (!response.ok) {
      const error: ErrorResponse = await response.json();

      // Handle specific errors
      if (error.detail.includes('rate limit')) {
        throw new Error('Terlalu banyak permintaan. Tunggu sebentar.');
      } else if (error.detail.includes('No relevant')) {
        throw new Error('Tidak menemukan informasi yang relevan.');
      } else {
        throw new Error(error.detail);
      }
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Gagal terhubung ke server. Periksa koneksi internet Anda.');
  }
}
```

---

## 📝 Complete React Example

```tsx
import React, { useState } from 'react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input,
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('/api/v1/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: input,
          session_id: sessionId,
        }),
      });

      const data = await response.json();

      // Extract sources
      const sourcesMatch = data.answer.match(/\n\nSumber:\n((?:- https?:\/\/[^\n]+\n?)+)/);
      const sources = sourcesMatch
        ? sourcesMatch[1].split('\n').map((s: string) => s.replace(/^- /, '').trim()).filter(Boolean)
        : undefined;

      const botMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.answer.replace(/\n\nSumber:\n((?:- https?:\/\/[^\n]+\n?)+)/, ''),
        sources,
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Maaf, terjadi kesalahan. Silakan coba lagi.',
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-interface">
      <div className="messages">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.role}`}>
            <div className="content">{msg.content}</div>
            {msg.sources && (
              <div className="sources">
                <strong>Sumber:</strong>
                {msg.sources.map((url, i) => (
                  <a key={i} href={url} target="_blank" rel="noopener noreferrer">
                    {url}
                  </a>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="loading">Memproses...</div>}
      </div>

      <form onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Tanyakan sesuatu..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Kirim
        </button>
      </form>
    </div>
  );
}
```

---

## 🎯 Key Points for UI

### What to Display:
✅ **User question**
✅ **AI answer** (clean text)
✅ **Source links** (clickable, extracted from answer)
✅ **Loading state** ("Mencari dokumen...")
✅ **Error messages** (friendly, actionable)

### What NOT to Display:
❌ Similarity scores (keep in metadata for debugging)
❌ Retrieved documents metadata
❌ Technical details (model, tokens, etc)
❌ Session ID (handle internally)

### Smart Behaviors:
- **Conversation Context**: Use same `session_id` for follow-up questions
- **Inline Sources**: Automatically shown when user asks ("berikan sumbernya")
- **Small Talk**: Greetings get brief responses without sources
- **Error Gracefully**: Show friendly messages, not technical errors

---

## 🔗 Related Documentation

- [Full API Documentation](./api/04-query.md)
- [Authentication Guide](./api/01-authentication.md)
- [API Reference](http://localhost:8000/docs)

---

**Ready to implement? Copy the examples and customize for your needs!** 🚀

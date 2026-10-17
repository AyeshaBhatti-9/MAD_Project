# QanoonSahib Backend: API Documentation for Frontend


**Purpose:** Pakistani labour law Q&A assistant (RAG). Users ask questions in plain language and get an answer with legal citations and a confidence score. They can optionally upload an employment contract (PDF) and ask questions about it.

| Item | Value |
|---|---|
| Base URL (local) | `http://127.0.0.1:8000` |
| Interactive docs | `{BASE_URL}/docs` (try every endpoint in the browser) |
| Machine-readable spec | `{BASE_URL}/openapi.json` (also saved in the repo) |
| Content type | `application/json`, except file upload (`multipart/form-data`) |
| Auth | `Authorization: Bearer <access_token>` |

---

## 1. Endpoint summary

| # | Method | Path | Auth | Purpose | Status |
|---|---|---|---|---|---|
| 1 | GET | `/health` | None | Server and database check | Live |
| 2 | POST | `/auth/signup` | None | Create an account | Live |
| 3 | POST | `/auth/login` | None | Sign in | Live |
| 4 | GET | `/auth/me` | **Required** | Current user | Live |
| 5 | POST | `/auth/forgot-password` | None | Request a password reset email | **Planned** |
| 6 | POST | `/auth/reset-password` | None | Set a new password using the emailed token | **Planned** |
| 7 | POST | `/chat/ask` | **Optional** (guest or user) | Ask a question | Live |
| 8 | GET | `/chat/conversations` | **Required** | List saved chats ("My questions") | Live |
| 9 | GET | `/chat/conversations/{id}` | **Required** | Open one saved chat | Live |
| 10 | DELETE | `/chat/conversations/{id}` | **Required** | Delete a saved chat | Live |
| 11 | POST | `/documents/upload` | **Optional** (guest or user) | Upload a contract PDF | Live |
| 12 | GET | `/documents` | **Required** | List saved documents | Live |
| 13 | GET | `/documents/{id}` | **Required** | Get one saved document with its text | Live |
| 14 | DELETE | `/documents/{id}` | **Required** | Delete a saved document | Live |

"Optional" auth means the endpoint works with no token (guest) and with a token (signed-in user). Behaviour differs, see section 3.

---

## 2. Screen to endpoint map (from the Figma design)

| Screen / action | Endpoint(s) |
|---|---|
| Landing: "Ask a question" (no account) | `POST /chat/ask` with no token |
| Landing / Sign in: "Sign in" | `POST /auth/login` |
| Create account (sign-up form) | `POST /auth/signup` |
| Forgot password? | `POST /auth/forgot-password`, then `POST /auth/reset-password` (planned, hide until released) |
| Continue without an account | No call. Use guest mode |
| Home: question box and Popular topics | `POST /chat/ask` (topic cards send a preset question) |
| Home: "Upload an employment contract" | `POST /documents/upload` |
| Answer view (answer, sources, confidence) | Response of `POST /chat/ask` |
| My questions (signed in) | `GET /chat/conversations`, then `GET /chat/conversations/{id}` |
| My questions (signed out) | No call. Show the sign-in prompt |
| Delete a question | `DELETE /chat/conversations/{id}` |
| Documents (signed in) | `GET /documents`, `GET /documents/{id}`, `DELETE /documents/{id}` |
| Documents (signed out, "current session") | No call. Keep the upload response in app state |
| Profile icon | `GET /auth/me` |
| Sign out | No call. Delete the stored token on the device |
| Help and about | Static, no API |

---

## 3. Guest vs signed-in behaviour

| | Guest (no token) | Signed in (token) |
|---|---|---|
| Ask a question | Yes | Yes |
| Answer saved to history | **No** (`conversation_id` is `null`) | **Yes** (`conversation_id` returned) |
| Follow-up questions | Frontend sends recent turns in `history` | Server loads history itself, send `conversation_id` |
| Upload a PDF | Yes, text returned, **not stored** (`saved: false`) | Yes, **stored** (`saved: true`, `id` returned) |
| Ask about a document | Send the text as `session_document` | Send `document_id` (or `session_document`) |
| List or open past chats | No | Yes |
| Saved documents list | No | Yes |

Frontend rule: a guest keeps the last 6 chat turns and the uploaded text in app memory only. They are lost when the app closes, which matches the Figma text "Signed-out uploads are only available during this session."

---

## 4. Authentication

- Signup and login return a JWT `access_token`. Valid for **7 days**.
- There are **no refresh tokens.** After expiry the user signs in again.
- Send it on every protected call: `Authorization: Bearer <access_token>`.
- Store it in secure storage (for React Native / Expo: `expo-secure-store`). Never in plain AsyncStorage.
- **Sign out** = delete the token locally. No server call.
- On `/chat/ask` and `/documents/upload`, an **invalid or expired token is treated as a guest** (no error). So after a 401 from any required endpoint, clear the token and show the sign-in screen.

---

## 5. Error format

All errors use the same shape:

```json
{ "detail": "Human-readable message" }
```

| Status | Meaning | Where | What the UI should do |
|---|---|---|---|
| 400 | Bad input (empty question, wrong file type, file too large) | ask, upload | Show `detail` |
| 401 | Missing, invalid or expired token; wrong login | protected, login | Clear token, show sign-in |
| 403 | Some versions return this when the `Authorization` header is missing entirely | protected | Treat like 401 |
| 404 | Item not found, or it belongs to another user | conversations, documents | Show "not found", refresh the list |
| 409 | Email already registered; document limit reached | signup, upload | Show `detail` |
| 422 | Validation error. **`detail` is an array here**, not a string. Example: `[{"loc":["body","email"],"msg":"value is not a valid email address","type":"value_error"}]` | any | Map `loc` to the form field |
| 429 | Rate limit exceeded. **Body is `{"error": "Rate limit exceeded: 10 per 1 minute"}`** (key is `error`, not `detail`) | rate-limited endpoints | Tell the user to wait a minute |
| 503 | AI service temporarily unavailable | `/chat/ask` | Show a "Try again" button. Nothing was saved |
| 500 | Unexpected server error | any | Generic error message |

### Rate limits (per IP address)

| Endpoint | Limit |
|---|---|
| `POST /chat/ask` | 10 per minute |
| `POST /documents/upload` | 5 per minute |
| `POST /auth/login` | 10 per minute |
| `POST /auth/signup` | 5 per minute |

---

## 6. Endpoints in detail

### 6.1 `GET /health`

No auth. Use it to check the server is up.

**200**
```json
{ "status": "ok", "collections": { "qanoon_labour": 2444, "qanoon_labour_clr": 10206 } }
```

---

### 6.2 `POST /auth/signup`

Create an account. Returns a token, so the user is signed in immediately.

**Request body**

| Field | Type | Rules |
|---|---|---|
| `email` | string | Valid email. Stored in lowercase |
| `name` | string | 1 to 100 characters |
| `password` | string | 8 to 72 characters (limit applies to bcrypt bytes, so avoid emoji and non-English characters in passwords) |

```json
{ "email": "ayesha@example.com", "name": "Ayesha", "password": "mypassword123" }
```

**201**
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": { "id": 1, "email": "ayesha@example.com", "name": "Ayesha" }
}
```

**Errors:** `409` `"Email already registered"`, `422` validation, `429`.

---

### 6.3 `POST /auth/login`

**Request body**

| Field | Type |
|---|---|
| `email` | string |
| `password` | string |

**200:** same shape as signup (`TokenResponse`).

**Errors:** `401` `"Incorrect email or password"` (same message whether the email or the password is wrong), `422`, `429`.

---

### 6.4 `GET /auth/me`

Auth required. Returns the signed-in user. Call it on app start if a token is stored. A `401` means the token is no longer valid.

**200**
```json
{ "id": 1, "email": "ayesha@example.com", "name": "Ayesha" }
```

**Errors:** `401` `"Invalid or expired token"` or `"User not found"`.

---

### 6.5 `POST /auth/forgot-password` (PLANNED, not live yet)

Starts a password reset. The backend emails a reset link or code. Contract below is the agreed plan and may change slightly. **Hide the "Forgot password?" button until this is released.**

**Request body**
```json
{ "email": "ayesha@example.com" }
```

**200 (always, even if the email is not registered, so attackers cannot discover which emails have accounts)**
```json
{ "message": "If an account exists for this email, a reset link has been sent." }
```

Planned rules: the reset token expires after 30 minutes and works once. Rate limit about 3 per hour per IP.

---

### 6.6 `POST /auth/reset-password` (PLANNED, not live yet)

**Request body**

| Field | Type | Rules |
|---|---|---|
| `token` | string | From the email |
| `new_password` | string | 8 to 72 characters |

```json
{ "token": "abc123...", "new_password": "newpassword456" }
```

**200**
```json
{ "message": "Password updated. Please sign in." }
```

**Errors (planned):** `400` `"Invalid or expired reset token"`, `422` validation. Existing sessions stay valid until their token expires (no token revocation).

---

### 6.7 `POST /chat/ask`: ask a question

Auth optional. This is the main endpoint.

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `question` | string | Yes | Must not be empty. English, Urdu or Roman Urdu |
| `conversation_id` | integer or null | No | Signed-in only. Omit or `null` to start a new chat. Send the id from a previous answer to continue it. Ignored for guests |
| `history` | array or null | No | **Guest only.** Last turns for follow-up questions. Items: `{ "role": "user" or "assistant", "content": "..." }`. Server uses the last 6. Ignored for signed-in users |
| `session_document` | string or null | No | Contract text (the `extracted_text` from upload). Server uses the first 8000 characters |
| `document_id` | integer or null | No | Signed-in only. Use a saved document. If sent, it takes priority over `session_document`. Ignored for guests |

Example, guest first question:
```json
{ "question": "How many days of annual leave do I get?" }
```

Example, guest follow-up:
```json
{
  "question": "and sick leave?",
  "history": [
    { "role": "user", "content": "How many days of annual leave do I get?" },
    { "role": "assistant", "content": "Workers are entitled to 14 days of annual leave [1]. ..." }
  ]
}
```

Example, signed in, follow-up about a saved contract:
```json
{ "question": "Is my notice period legal?", "conversation_id": 7, "document_id": 3 }
```

**200 response**

| Field | Type | Notes |
|---|---|---|
| `conversation_id` | integer or null | `null` for guests. Save it to continue the chat |
| `answer` | string | Plain text with inline markers like `[1]`, `[2]`. Ends with a legal disclaimer line. May contain line breaks |
| `citations` | array | Law provisions behind the answer. Empty for greetings |
| `xai` | object or null | Confidence info. `null` for greetings and small talk |

`citations[]` items:

| Field | Type | Notes |
|---|---|---|
| `index` | integer | Matches the `[N]` markers in `answer`. Can skip numbers because duplicate sections are removed |
| `law_name` | string | e.g. an Act or Ordinance name. Can be `"Unknown Act"` |
| `section_number` | string | Can be empty `""` or `"N/A"` |
| `section_title` | string | Can be empty |
| `excerpt` | string | Up to 500 characters of the provision text |
| `relevance_score` | number 0 to 1 | Relative to the other sources **in this answer** (the top one is usually 1.0). Do not compare across answers |
| `why_relevant` | string | One sentence. **Can be empty `""`**, so hide the line if empty |

`xai` object:

| Field | Type | Notes |
|---|---|---|
| `confidence_label` | `"High"`, `"Medium"` or `"Low"` | Show as a badge |
| `confidence_score` | number 0 to 1 | Overall confidence. Good for a progress bar |
| `top_rerank_score` | number | Raw internal score. Not for display |
| `num_sources_used` | integer | Number of sources retrieved |

Example response:
```json
{
  "conversation_id": 7,
  "answer": "Workers are entitled to 14 days of annual leave after one year of service [1]. ... ⚖️ Note: This is general legal information, not legal advice. For your specific situation, consult a qualified labour lawyer.",
  "citations": [
    {
      "index": 1,
      "law_name": "Example Labour Act",
      "section_number": "49",
      "section_title": "Annual leave",
      "excerpt": "A worker shall be allowed ...",
      "relevance_score": 1.0,
      "why_relevant": "This section states the minimum annual leave entitlement."
    }
  ],
  "xai": { "confidence_label": "High", "confidence_score": 0.91, "top_rerank_score": 5.2, "num_sources_used": 5 }
}
```

Greeting example (`"hi"`): `{ "conversation_id": 8, "answer": "Hello! ...", "citations": [], "xai": null }`

**Frontend notes**
- Turn `[1]`, `[2]` in `answer` into tappable chips (regex `\[(\d+)\]`) that open the matching `citations[].index`.
- Responses take **several seconds**. Show a loading state and set the client timeout to **at least 60 seconds**.
- Disable the send button while a request is in flight (rate limit is 10 per minute).
- A low confidence label means the retrieved law was only a weak match. Consider showing a short "verify with a lawyer" hint.

**Errors:** `400` `"Question cannot be empty"`, `404` `"Conversation not found"` or `"Document not found"`, `422`, `429`, `503`.

---

### 6.8 `GET /chat/conversations`: "My questions" list

Auth required. Newest first.

**200**
```json
[
  { "id": 7, "title": "How many days of annual leave do I get?", "updated_at": "2026-10-18T02:10:00" },
  { "id": 6, "title": "Is my notice period legal?", "updated_at": "2026-10-17T19:42:11" }
]
```

`title` is the first 60 characters of the first question. Dates are ISO 8601 in **UTC** and may come **without** a `Z` or offset, so treat them as UTC when converting to local time.

---

### 6.9 `GET /chat/conversations/{id}`: open a saved chat

Auth required. Returns every message in order, including stored citations and confidence, so an old chat looks the same as when it was asked.

**200**
```json
{
  "id": 7,
  "title": "How many days of annual leave do I get?",
  "messages": [
    { "id": 13, "role": "user", "content": "How many days of annual leave do I get?",
      "citations": null, "xai": null, "created_at": "2026-10-18T02:10:00" },
    { "id": 14, "role": "assistant", "content": "Workers are entitled to ... [1] ...",
      "citations": [ { "index": 1, "law_name": "...", "section_number": "49", "section_title": "...", "excerpt": "...", "relevance_score": 1.0, "why_relevant": "..." } ],
      "xai": { "confidence_label": "High", "confidence_score": 0.91, "top_rerank_score": 5.2, "num_sources_used": 5 },
      "created_at": "2026-10-18T02:10:04" }
  ]
}
```

`role` is `"user"` or `"assistant"`. User messages have `citations: null` and `xai: null`. Assistant messages from greetings have `citations: []` and `xai: null`.

**Errors:** `401`, `404` (not found, or it belongs to another user).

To continue the chat, call `POST /chat/ask` with `conversation_id`.

---

### 6.10 `DELETE /chat/conversations/{id}`

Auth required. Deletes the chat and all its messages permanently.

**204** (no body). **Errors:** `401`, `404`.

---

### 6.11 `POST /documents/upload`: upload a contract

Auth optional. Content type is `multipart/form-data` with one field named **`file`**.

| Rule | Value |
|---|---|
| Type | PDF only (file name must end in `.pdf`) |
| Max size | 5 MB |
| Scanned or image-only PDFs | Not supported (no text can be extracted) |
| Max saved documents per signed-in user | 20 |
| Rate limit | 5 per minute |

curl example:
```bash
curl -X POST "http://127.0.0.1:8000/documents/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@Employment-contract.pdf"
```

**200**

| Field | Type | Notes |
|---|---|---|
| `id` | integer or null | `null` for guests |
| `filename` | string | |
| `extracted_text` | string | Full text of the PDF. Guests must keep this and send it later as `session_document` |
| `char_count` | integer | |
| `saved` | boolean | `false` for guests, `true` for signed-in users |

```json
{ "id": 3, "filename": "Employment-contract.pdf", "extracted_text": "EMPLOYMENT AGREEMENT ...", "char_count": 5821, "saved": true }
```

**Errors**

| Status | `detail` |
|---|---|
| 400 | `"Only PDF files accepted"` |
| 400 | `"File too large (max 5 MB)"` |
| 422 | `"Could not extract text from this PDF. It may be scanned/image-based."` |
| 409 | `"Document limit reached (20). Delete one to upload more."` |
| 429 | Rate limit |

Note: for long contracts only the first 8000 characters are used when answering questions.

---

### 6.12 `GET /documents`: saved documents list

Auth required. Newest first. Does **not** include the text, to keep the list small.

**200**
```json
[ { "id": 3, "filename": "Employment-contract.pdf", "char_count": 5821, "created_at": "2026-10-18T02:20:00" } ]
```

---

### 6.13 `GET /documents/{id}`

Auth required. Same as the list item plus `extracted_text`.

**200**
```json
{ "id": 3, "filename": "Employment-contract.pdf", "char_count": 5821, "created_at": "2026-10-18T02:20:00", "extracted_text": "EMPLOYMENT AGREEMENT ..." }
```

**Errors:** `401`, `404`.

---

### 6.14 `DELETE /documents/{id}`

Auth required. **204** (no body). **Errors:** `401`, `404`.

---

## 7. Typical flows

**Guest asks a question**
1. `POST /chat/ask` with `{ question }`.
2. Show `answer`, `citations`, `xai`.
3. For a follow-up, send the next `question` plus `history` (the last turns kept in app state).

**Guest uploads a contract and asks about it**
1. `POST /documents/upload` and keep `extracted_text` in app state.
2. `POST /chat/ask` with `{ question, session_document: extracted_text }` on every question while the document is active.

**Sign up, then ask and save**
1. `POST /auth/signup` and store `access_token`.
2. `POST /chat/ask` with the token. Keep the returned `conversation_id`.
3. Next message in the same chat: send the same `conversation_id`. No `history` needed.

**Signed-in contract flow**
1. `POST /documents/upload` with the token, then keep the returned `id`.
2. `POST /chat/ask` with `{ question, document_id }`.

**My questions screen**
1. `GET /chat/conversations` for the list.
2. Tap an item and call `GET /chat/conversations/{id}`.
3. Continue with `POST /chat/ask` and `conversation_id`.

---

## 8. TypeScript types (for the frontend team)

```ts
export interface User { id: number; email: string; name: string }
export interface TokenResponse { access_token: string; token_type: "bearer"; user: User }

export interface ChatTurn { role: "user" | "assistant"; content: string }

export interface AskRequest {
  question: string;
  conversation_id?: number | null;
  history?: ChatTurn[] | null;          // guests only
  session_document?: string | null;
  document_id?: number | null;          // signed-in only
}

export interface Citation {
  index: number;
  law_name: string;
  section_number: string;               // may be "" or "N/A"
  section_title: string;                // may be ""
  excerpt: string;
  relevance_score: number;              // 0..1, relative within this answer
  why_relevant: string;                 // may be ""
}

export interface XAIInfo {
  confidence_label: "High" | "Medium" | "Low";
  confidence_score: number;             // 0..1
  top_rerank_score: number;
  num_sources_used: number;
}

export interface AskResponse {
  conversation_id: number | null;       // null for guests
  answer: string;
  citations: Citation[];
  xai: XAIInfo | null;                  // null for greetings
}

export interface ConversationOut { id: number; title: string; updated_at: string }

export interface MessageOut {
  id: number;
  role: "user" | "assistant";
  content: string;
  citations: Citation[] | null;
  xai: XAIInfo | null;
  created_at: string;
}
export interface ConversationDetail { id: number; title: string; messages: MessageOut[] }

export interface DocumentOut { id: number; filename: string; char_count: number; created_at: string }
export interface DocumentDetail extends DocumentOut { extracted_text: string }
export interface UploadResponse {
  id: number | null;                    // null for guests
  filename: string;
  extracted_text: string;
  char_count: number;
  saved: boolean;
}
```

---

## 9. Notes and known limits

| Topic | Detail |
|---|---|
| Language | Answers follow the language of the question (English, Urdu, Roman Urdu). The "Simple English" label in the UI is only a label for now, there is no language parameter yet |
| Contract length | Only the first 8000 characters of a contract are used when answering |
| Scanned PDFs | Not supported (no OCR) |
| Not legal advice | Every legal answer ends with a disclaimer line, so do not strip it |
| CORS | Open to all origins during development. It will be restricted to the real app origin before deployment |
| Dates | ISO 8601, UTC, may lack a timezone suffix. Treat as UTC |
| Session length | Tokens last 7 days, no refresh |
| Delete account | Not available yet |
| Forgot password | Planned (sections 6.5 and 6.6), not live |
| Changes | Check `/openapi.json` for the latest contract. If it differs from this file, the OpenAPI file is correct, and tell the backend team |
# HR RAG Chatbot

A production-ready HR chatbot backend that answers employee status queries and internal policy questions using a hybrid RAG pipeline.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange?logo=google&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-vector_store-purple)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## Overview

HR RAG Chatbot routes natural language questions through a multi-stage pipeline:

- **Employee status questions** → answered from live HR data (SQLite / Firestore)
- **Policy & procedure questions** → answered from ingested internal documents via RAG
- **Out-of-scope questions** → politely declined

The system classifies intent using a three-layer approach (embedding k-NN → keyword regex → LLM fallback), retrieves relevant document chunks with role-based access control, reranks them with a cross-encoder, and generates answers with Gemini.

---

## Architecture

```
POST /api/chat
      │
      ├── Authentication
      │     ├── X-API-Key (demo mode)
      │     └── Firebase Bearer token (production)
      │
      ├── Intent Classification
      │     ├── 1. Embedding k-NN  (BGE-M3, ~20 ms)
      │     ├── 2. Keyword regex   (~1 ms)
      │     └── 3. LLM fallback    (Gemini, ~2 s)
      │
      ├── [employee_status] ──► SQLite / Firestore
      │
      ├── [document_qa]
      │     ├── Vector retrieval   (ChromaDB + BGE-M3)
      │     ├── Reranking          (BGE-reranker-v2-m3)
      │     └── RBAC filter        (role-based access)
      │
      └── Answer generation (Gemini 2.5 Flash)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI · Uvicorn |
| LLM | Google Gemini 2.5 Flash |
| Embeddings | `BAAI/bge-m3` (local · GPU) |
| Reranker | `BAAI/bge-reranker-v2-m3` (local · GPU) |
| Vector Store | ChromaDB (persistent) |
| Database | SQLite · SQLAlchemy |
| Authentication | Firebase Auth · API key (demo) |
| Notifications | Firebase Cloud Messaging |

---

## Features

- **Hybrid intent classification** — BGE-M3 k-NN + regex + LLM, extensible by editing a JSON file
- **Reranked RAG** — vector retrieval followed by cross-encoder reranking for precision
- **Role-based access control** — document access filtered per user role at query time
- **Dual data source** — Firestore for production, SQLite fallback for local dev
- **Conversation history** — last 3 exchanges persisted in SQLite per session
- **Response cache** — TTL-based in-memory cache for repeated `document_qa` queries
- **Request logging** — every query logged with intent, latency, user, and role

---

## Requirements

- Python 3.11+
- CUDA-capable GPU (recommended — embedding and reranker models run on GPU)
- Google Gemini API key
- Firebase service account *(optional — required for production auth and Firestore)*

---

## Getting Started

**1. Clone and install**

```bash
git clone https://github.com/your-org/hr-rag-chatbot.git
cd hr-rag-chatbot

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
```

**2. Configure environment**

```bash
cp .env.example .env
# Open .env and set GOOGLE_API_KEY
```

**3. Seed demo data**

```bash
python -m app.db.seed
```

**4. Start the server**

```bash
uvicorn app.main:app --reload --port 8000
```

| URL | Description |
|---|---|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/health | Health check |

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `GOOGLE_API_KEY` | Gemini API key **(required)** | — |
| `LOCAL_EMBEDDING_MODEL` | HuggingFace embedding model | `BAAI/bge-m3` |
| `RERANKER_MODEL` | Cross-encoder reranker model | `BAAI/bge-reranker-v2-m3` |
| `USE_RERANKER` | Enable / disable reranking | `true` |
| `RERANKER_MIN_SCORE` | Minimum reranker score (0–1) | `0.3` |
| `DATABASE_URL` | SQLite connection string | `sqlite:///data/sqlite/hr.db` |
| `CHROMA_PERSIST_DIR` | ChromaDB storage directory | `data/chroma` |
| `DOCS_DIR` | Source documents directory | `data/docs` |
| `FIREBASE_PROJECT_ID` | Firebase project ID | — |
| `FIREBASE_CREDENTIALS_PATH` | Path to service account JSON | `firebase-service-account.json` |

---

## Authentication

### Demo mode (local development)

Pass one of the following keys in the `X-API-Key` header:

| Key | Role | Department |
|---|---|---|
| `demo_employee_001` | employee | engineering |
| `demo_hr_001` | hr | hr |
| `demo_manager_001` | manager | engineering |
| `demo_admin_001` | admin | management |

### Production mode

```http
Authorization: Bearer <firebase_id_token>
```

---

## API Reference

### Send a message

```http
POST /api/chat
X-API-Key: demo_employee_001
Content-Type: application/json

{
  "message": "What is the annual leave policy?",
  "session_id": "sess_001"
}
```

```json
{
  "answer": "Employees are entitled to 12 days of annual leave per year...",
  "intent": "document_qa",
  "sources": [
    { "title": "Company Handbook", "page": 12, "file": "handbook.pdf" }
  ],
  "error": null
}
```

### Other endpoints

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| `GET` | `/health` | No | Service health check |
| `POST` | `/api/chat` | Yes | Main chat endpoint |
| `POST` | `/api/docs/ingest` | admin | Upload and index a document |
| `GET` | `/api/docs/stats` | Yes | Vector store statistics |
| `GET` | `/api/employees` | hr · manager · admin | List employees |
| `GET` | `/api/employees/on-leave` | hr · manager · admin | Employees currently on leave |
| `GET` | `/api/logs` | admin | Query history and latency log |
| `POST` | `/api/notify` | hr · admin | Send push notification via FCM |

---

## Ingesting Documents

Place files in `data/docs/` or upload via API. Supported formats: `.pdf`, `.docx`, `.txt`

```bash
curl -X POST http://localhost:8000/api/docs/ingest \
  -H "X-API-Key: demo_admin_001" \
  -F "file=@data/docs/handbook.pdf" \
  -F "category=policy" \
  -F "access_level=all"
```

Access levels: `all` (visible to everyone) or a specific role (`hr`, `manager`, `admin`).

---

## Extending Intent Classification

The intent classifier uses embedding k-NN — no code changes needed to add new phrasings.

Edit `app/data/intent_examples.json` and restart the server:

```json
{
  "employee_status": [
    "Who is on leave today?",
    "Show me the attendance list for this morning"
  ],
  "document_qa": [
    "How many days of annual leave do I get?",
    "What is the remote work policy?"
  ],
  "out_of_scope": [
    "What is the weather like today?",
    "Recommend a restaurant near me"
  ]
}
```

To add a new intent category, add a new key with at least 10–15 example questions and restart.

---

## Project Structure

```
hr-rag-chatbot/
├── app/
│   ├── api/
│   │   ├── routes_chat.py           # POST /api/chat
│   │   ├── routes_docs.py           # Document ingestion
│   │   ├── routes_employee.py       # Employee data endpoints
│   │   ├── routes_logs.py           # Query log viewer
│   │   ├── routes_notify.py         # FCM notifications
│   │   └── routes_health.py         # Health check
│   ├── core/
│   │   ├── config.py                # Settings singleton
│   │   └── security.py              # Auth — demo keys + Firebase
│   ├── data/
│   │   └── intent_examples.json     # k-NN classifier training examples
│   ├── db/
│   │   ├── models.py                # SQLAlchemy table definitions
│   │   ├── session.py               # DB session factory
│   │   └── seed.py                  # Demo data seeder
│   ├── prompts/
│   │   ├── system_prompt.txt        # LLM system instructions
│   │   ├── answer_prompt.txt        # Answer generation template
│   │   └── router_prompt.txt        # Intent classification prompt
│   ├── services/
│   │   ├── rag_service.py           # Main orchestration layer
│   │   ├── intent_service.py        # Intent classification (regex + LLM)
│   │   ├── intent_classifier_service.py  # BGE-M3 k-NN classifier
│   │   ├── retriever_service.py     # ChromaDB vector search + RBAC
│   │   ├── reranker_service.py      # Cross-encoder reranking
│   │   ├── embedding_service.py     # BGE-M3 embedding wrapper
│   │   ├── ingest_service.py        # Document ingestion pipeline
│   │   ├── gemini_service.py        # Gemini LLM client
│   │   ├── employee_service.py      # SQLite HR queries
│   │   └── firestore_employee_service.py  # Firestore HR queries
│   └── main.py                      # App entry point + startup warmup
├── data/
│   ├── docs/                        # Source documents (PDF, DOCX, TXT)
│   ├── chroma/                      # ChromaDB vector store (auto-created)
│   └── sqlite/                      # SQLite database (auto-created)
├── .env.example
├── requirements.txt
└── CHANGES.md
```

---

## Known Limitations

- **In-process cache** — intent and response caches are not shared across multiple Uvicorn workers
- **No rate limiting** — the `/api/chat` endpoint has no request throttling
- **CORS** — currently allows all origins (`*`); restrict for production
- **Gemini latency** — API response time is variable (5–19 s) and outside server control
- **`.doc` format** — legacy Word files require MS Word COM automation (Windows only); use `.docx` instead

# LocalDocRAG — RAG Document Intelligence System

> Upload PDFs. Ask questions. Get grounded, page-cited answers. Runs 100% locally on a Raspberry Pi — no cloud required.

---

## Architecture

```
HOME NETWORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Browser (phone / laptop / tablet)
  https://192.168.x.x  or  https://localdocrag.local
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━
                                           │ HTTPS
                             ┌─────────────▼──────────────────────┐
                             │   Raspberry Pi 4/5 (Docker)        │
                             │                                    │
                             │  ┌──────────────────────────────┐  │
                             │  │  nginx (ports 80/443)        │  │
                             │  │  SSL termination             │  │
                             │  │  Rate limiting (30 req/min)  │  │
                             │  └─────────┬────────┬───────────┘  │
                             │            │        │              │
                             │  ┌─────────▼──┐  ┌──▼────────────┐ │
                             │  │  Frontend  │  │  FastAPI      │ │
                             │  │  React 18  │  │  Backend      │ │
                             │  │  + Vite    │  │  Port 8000    │ │
                             │  │  Port 80   │  └──────┬────────┘ │
                             │  └────────────┘         │          │
                             │                ┌────────▼────────┐ │
                             │                │  PostgreSQL 16  │ │
                             │                │  + pgvector     │ │
                             │                │  Port 5432      │ │
                             │                └─────────────────┘ │
                             │                                    │
                             │  ┌──────────────────────────────┐  │
                             │  │  Ollama (optional)           │  │
                             │  │  Port 11434 (internal only)  │  │
                             │  │  qwen2.5:14b + nomic-embed   │  │
                             │  └──────────────────────────────┘  │
                             └────────────────────────────────────┘
```

**RAG Pipeline:**

```
PDF Upload → pypdf parse → RecursiveCharacterTextSplitter (chunk=800, overlap=150)
  → OllamaEmbeddings / OpenAIEmbeddings → pgvector INSERT

Question → embed → pgvector cosine similarity search (TOP_K=5)
  → context + LLM prompt → ChatOllama / ChatOpenAI → answer + cited sources
```

---

## Tech Stack

| Layer           | Technology                                                                |
| --------------- | ------------------------------------------------------------------------- |
| Backend         | Python 3.11, FastAPI 0.111, uvicorn                                       |
| Authentication  | JWT (python-jose), bcrypt                                                 |
| Rate limiting   | slowapi (FastAPI) + nginx                                                 |
| RAG pipeline    | LangChain 0.2, LangChain-OpenAI, LangChain-Anthropic, LangChain-Community |
| Vector database | PostgreSQL 16 + pgvector                                                  |
| ORM             | SQLAlchemy 2.0 (async) + psycopg3                                         |
| PDF parsing     | pypdf 4.2                                                                 |
| Evaluation      | RAGAS 0.1.9 (faithfulness, relevancy, precision, recall)                  |
| Frontend        | React 18, Vite 5, Tailwind CSS 3, react-markdown                          |
| Proxy / SSL     | nginx:alpine (self-signed TLS)                                            |
| Containers      | Docker + Docker Compose v3.9                                              |
| CI/CD           | GitHub Actions (test + lint + docker build)                               |

---

## LLM Providers

Switch providers with a single env var — zero code changes:

| `LLM_PROVIDER` | Chat Model                        | Embeddings                     | Cost           |
| -------------- | --------------------------------- | ------------------------------ | -------------- |
| `ollama`       | qwen2.5:14b (or any Ollama model) | nomic-embed-text (768d)        | **Free**       |
| `openai`       | gpt-4o-mini                       | text-embedding-3-small (1536d) | ~$0.001/query  |
| `anthropic`    | claude-haiku-4-5                  | OpenAI (fallback)              | ~$0.0008/query |

**Raspberry Pi 5 16GB model guide:**

| Model               | Size   | Best for                                      |
| ------------------- | ------ | --------------------------------------------- |
| `qwen2.5:14b`       | 8.2 GB | **Recommended** — best document understanding |
| `deepseek-r1:14b`   | 8.5 GB | Analysis and reasoning tasks                  |
| `gemma2:27b:q4_K_M` | 15 GB  | Maximum quality (uses nearly all RAM)         |
| `llama3.1:8b`       | 4.7 GB | Fast, well-tested fallback                    |

---

## Quick Start — Local Testing with Ollama (No API Keys Needed)

This section walks you through the **complete setup from scratch** using only Ollama (fully local, no OpenAI or Anthropic key required).

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Mac/Windows) or Docker Engine + Compose plugin (Linux/Pi)
- That's it — Python, Node.js, and Ollama are all handled inside Docker containers

---

### Step 1 — Clone the repo

```bash
git clone https://github.com/alinjfz/localdocrag.git
cd docmind
```

---

### Step 2 — Generate your credentials

You need two values before you can start: a bcrypt password hash and a JWT secret key.

**Option A — Using Docker (no Python needed locally):**

```bash
# Generate a bcrypt hash for your chosen password (replace 'mypassword'):
docker run --rm python:3.11-slim \
  python3 -c "import bcrypt; print(bcrypt.hashpw(b'mypassword', bcrypt.gensalt()).decode())"

# Generate a random JWT secret:
docker run --rm python:3.11-slim \
  python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Option B — If you have Python 3 installed locally:**

```bash
pip install bcrypt   # only needed if not already installed
python3 -c "import bcrypt; print(bcrypt.hashpw(b'mypassword', bcrypt.gensalt()).decode())"
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Both commands print one line of output each. Copy those values — you'll need them in the next step.

---

### Step 3 — Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` in any text editor and set these values:

```bash
# Paste the bcrypt hash from Step 2:
APP_PASSWORD_HASH=$2b$12$...your_hash_here...

# Paste the random secret from Step 2:
JWT_SECRET_KEY=your64charhexstring

# Choose your password for the PostgreSQL database (anything you like):
DB_PASSWORD=pick_a_db_password

# Keep these as-is for Ollama local mode:
LLM_PROVIDER=ollama
OLLAMA_LLM_MODEL=llama3.2:3b    # fast 2GB model, good for testing
OLLAMA_EMBED_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=768

# Leave API keys blank:
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

> **Model size guide** — change `OLLAMA_LLM_MODEL` to suit your machine:
>
> - `llama3.2:3b` — 2 GB RAM, fast, good for testing
> - `llama3.1:8b` — 4.7 GB RAM, better quality
> - `qwen2.5:14b` — 8.2 GB RAM, best quality (Pi 5 16GB / desktop)

Also update `DATABASE_URL` to use the password you picked:

```bash
DATABASE_URL=postgresql+psycopg://localdocrag_user:pick_a_db_password@db:5432/localdocrag
```

---

### Step 4 — Start the full stack

```bash
docker-compose --profile ollama up --build
```

This starts 5 services: **db** (PostgreSQL + pgvector), **backend** (FastAPI), **frontend** (React), **nginx** (HTTPS proxy), and **ollama**.

Wait until you see lines like:

```
backend-1  | INFO:     Application startup complete.
frontend-1 | /docker-entrypoint.sh: Configuration complete; ready for start up
nginx-1    | ...start worker processes
```

Leave this terminal running. Open a new terminal tab for the next steps.

---

### Step 5 — Pull Ollama models (first time only)

In a **new terminal tab**, run:

```bash
# Pull the embedding model (~274 MB):
docker-compose --profile ollama exec ollama ollama pull nomic-embed-text

# Pull the chat model (replace with the model you chose in .env):
docker-compose --profile ollama exec ollama ollama pull llama3.2:3b
```

This downloads the models inside the Docker container. It takes a few minutes on first run. You only need to do this once — the models persist in a Docker volume.

---

### Step 6 — Open the app in your browser

Go to: **`https://localhost`**

Your browser will show a certificate warning ("Your connection is not private" / "Potential Security Risk"). This is expected — the app uses a self-signed certificate for local HTTPS.

- **Chrome:** Click "Advanced" → "Proceed to localhost (unsafe)"
- **Firefox:** Click "Advanced…" → "Accept the Risk and Continue"
- **Safari:** Click "Show Details" → "visit this website"

You'll see the LocalDocRAG login page.

---

### Step 7 — Log in

- **Username:** whatever you set as `APP_USERNAME` in `.env` (default: `admin`)
- **Password:** the plain-text password you used when generating the hash in Step 2 (e.g. `mypassword`)

---

### Step 8 — Test the RAG pipeline

1. **Upload a PDF** — click the upload zone in the sidebar, drag a PDF in, wait for "Processing complete"
2. **Ask a question** — type a question about the document in the chat box and hit Enter
3. You'll get an answer with page citations. The first query may be slow (~10–30 sec) while Ollama loads the model into memory. Subsequent queries are faster.

---

### Step 9 — Access from phone or tablet on your home network

First, find your machine's local IP address:

```bash
# Mac:
ipconfig getifaddr en0

# Linux / Raspberry Pi:
hostname -I | awk '{print $1}'

# Windows (in PowerShell):
(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias Wi-Fi).IPAddress
```

Then on your phone or tablet (connected to the same Wi-Fi), open:

**`https://192.168.1.XXX`** (replace with your actual IP)

Accept the certificate warning the same way as in Step 6. The full app works from any device on your network.

---

### What works without API keys

| Feature                             | Ollama only                                                                                    |
| ----------------------------------- | ---------------------------------------------------------------------------------------------- |
| PDF upload + processing             | Yes                                                                                            |
| Q&A with page citations             | Yes                                                                                            |
| Document list / delete              | Yes                                                                                            |
| Login / JWT auth                    | Yes                                                                                            |
| RAGAS evaluation (`/api/evaluate/`) | No — returns HTTP 400 with a clear message explaining that OpenAI is required as the judge LLM |

---

### Stopping and restarting

```bash
# Stop all containers (keeps data):
docker-compose --profile ollama down

# Restart later (models already pulled, no --build needed):
docker-compose --profile ollama up

# Stop and wipe all data (database + model volumes):
docker-compose --profile ollama down -v
```

---

### Troubleshooting

**"connection refused" or blank page:**
Check that all containers started: `docker-compose --profile ollama ps`. All should show `Up` or `healthy`.

**Login fails with 401:**
The password hash in `.env` doesn't match your password. Re-run the hash generation command from Step 2 and paste the new hash into `.env`, then restart: `docker-compose --profile ollama restart backend`.

**Ollama query times out:**
The model is loading. Wait ~30 seconds and try again. If it persists: `docker-compose --profile ollama logs ollama` to check for errors. Ensure you pulled the model that matches `OLLAMA_LLM_MODEL` in your `.env`.

**"embedding dimension mismatch" error:**
You changed `OLLAMA_EMBED_MODEL` or `EMBEDDING_DIMENSION` after uploading documents. Drop and recreate the chunks table: `docker-compose --profile ollama down -v` then re-upload your PDFs.

**Browser keeps redirecting to HTTP:**
Open `https://localhost` explicitly (with `https://`). The app redirects port 80 → 443 automatically.

---

## Quick Start — Cloud API Mode (OpenAI / Anthropic)

If you have an API key, set these in `.env` and restart without the `ollama` profile:

```bash
LLM_PROVIDER=openai          # or: anthropic
OPENAI_API_KEY=sk-...        # your key
EMBEDDING_DIMENSION=1536     # OpenAI embeddings are 1536-dimensional
OLLAMA_LLM_MODEL=            # not used in OpenAI mode
```

```bash
docker-compose up --build    # no --profile ollama needed
```

For Anthropic, also set `OPENAI_API_KEY` — Anthropic uses OpenAI's embedding API as a fallback when no native embedding model is specified.

> **Note:** `OPENAI_API_KEY` is also required if you want to use the RAGAS evaluation endpoint (`/api/evaluate/`), even when `LLM_PROVIDER=ollama`, because RAGAS uses OpenAI as its judge LLM.

---

## Raspberry Pi Setup Guide

### Install Docker on Pi (Raspbian / Ubuntu)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install docker-compose plugin
sudo apt-get install docker-compose-plugin
```

### Deploy LocalDocRAG on Pi

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/localdocrag.git
cd localdocrag

# Set up .env (see Quick Start — Local Testing section above)
cp .env.example .env
nano .env  # paste your bcrypt hash and JWT secret

# Start (Ollama profile for local models)
docker-compose --profile ollama up -d --build

# Pull Ollama models
docker-compose --profile ollama exec ollama ollama pull nomic-embed-text
docker-compose --profile ollama exec ollama ollama pull qwen2.5:14b  # Pi 5 16GB
# Or for Pi 4 8GB: ollama pull llama3.2:3b
```

### Access from home network

```bash
# Find your Pi's IP address:
hostname -I

# Then on any device on your home Wi-Fi:
# https://192.168.1.XXX   (replace with your Pi's IP)
```

### Optional: mDNS hostname (localdocrag.local)

```bash
# On the Pi:
sudo apt install avahi-daemon
sudo systemctl enable --now avahi-daemon

# Now accessible at: https://localdocrag.local
```

### Optional: Auto-start on boot

```bash
# Create a systemd service or add to /etc/rc.local:
cd /home/pi/docmind && docker-compose --profile ollama up -d
```

---

## Environment Variables

| Variable              | Default                    | Description                                |
| --------------------- | -------------------------- | ------------------------------------------ |
| `APP_USERNAME`        | `admin`                    | Login username                             |
| `APP_PASSWORD_HASH`   | —                          | bcrypt hash of your password               |
| `JWT_SECRET_KEY`      | —                          | Random 32+ char string for JWT signing     |
| `JWT_EXPIRE_MINUTES`  | `480`                      | Session duration (8 hours)                 |
| `LLM_PROVIDER`        | `ollama`                   | `openai` \| `anthropic` \| `ollama`        |
| `OPENAI_API_KEY`      | —                          | Required for OpenAI / RAGAS eval           |
| `ANTHROPIC_API_KEY`   | —                          | Required for Anthropic                     |
| `OLLAMA_BASE_URL`     | `http://ollama:11434`      | Ollama service URL                         |
| `OLLAMA_LLM_MODEL`    | `qwen2.5:14b`              | Chat model name                            |
| `OLLAMA_EMBED_MODEL`  | `nomic-embed-text`         | Embedding model name                       |
| `DATABASE_URL`        | postgresql+psycopg://…     | Async psycopg3 URL                         |
| `DB_PASSWORD`         | `localdocrag_secret_change_me` | PostgreSQL password                    |
| `CHUNK_SIZE`          | `800`                      | Token target per chunk                     |
| `CHUNK_OVERLAP`       | `150`                      | Overlap between chunks                     |
| `TOP_K_RETRIEVAL`     | `5`                        | Number of chunks to retrieve               |
| `MAX_FILE_SIZE_MB`    | `20`                       | Max PDF upload size                        |
| `EMBEDDING_DIMENSION` | `768`                      | Must match model (768=Ollama, 1536=OpenAI) |
| `ALLOWED_ORIGINS`     | `https://localhost,…`      | CORS origins (add your Pi's IP)            |

---

## API Reference

All endpoints require `Authorization: Bearer <token>` except `/api/auth/login`.

Interactive docs: `https://localhost/api/docs`

### Auth

| Method | Path              | Description         |
| ------ | ----------------- | ------------------- |
| `POST` | `/api/auth/login` | Login → returns JWT |

```json
// POST /api/auth/login
{ "username": "admin", "password": "yourpassword" }

// Response
{ "access_token": "eyJ…", "token_type": "bearer", "expires_in": 28800 }
```

### Documents

| Method   | Path                    | Description                      |
| -------- | ----------------------- | -------------------------------- |
| `POST`   | `/api/documents/upload` | Upload PDF (multipart/form-data) |
| `GET`    | `/api/documents/`       | List all documents               |
| `DELETE` | `/api/documents/{id}`   | Delete document + all chunks     |

```json
// POST /api/documents/upload → 201
{
  "id": "uuid",
  "filename": "report.pdf",
  "chunk_count": 42,
  "created_at": "2026-03-28T10:00:00Z",
  "embedding_provider": "ollama"
}
```

### Query

| Method | Path          | Description                      |
| ------ | ------------- | -------------------------------- |
| `POST` | `/api/query/` | Ask a question, get cited answer |

```json
// Request
{ "question": "What are the key findings?", "document_id": "uuid-or-null" }

// Response
{
  "answer": "The key findings are… (Page 3)",
  "sources": [
    { "content": "The study found…", "page_number": 3, "score": 0.92 }
  ],
  "question": "What are the key findings?",
  "document_id": "uuid"
}
```

### Evaluation

| Method | Path             | Description          |
| ------ | ---------------- | -------------------- |
| `POST` | `/api/evaluate/` | Run RAGAS evaluation |

```json
// Request
{
  "test_cases": [
    { "question": "What is X?", "ground_truth": "X is Y.", "document_id": "uuid" }
  ]
}

// Response
{
  "metrics": {
    "faithfulness": 0.91,
    "answer_relevancy": 0.88,
    "context_precision": 0.85,
    "context_recall": 0.79
  },
  "num_samples": 1
}
```

---

## Running Tests

```bash
# Option 1: With the test compose database
docker-compose -f docker-compose.test.yml up -d
cd backend
DATABASE_URL=postgresql+psycopg://localdocrag_user:test_secret@localhost:5433/localdocrag_test \
  pytest tests/ -v
docker-compose -f docker-compose.test.yml down

# Option 2: Tests mock all DB + LLM calls (no DB needed)
cd backend
pip install -r requirements.txt
pytest tests/ -v  # uses os.environ defaults in conftest.py
```

Tests cover:

- **test_auth.py** (5) — JWT login, wrong credentials, protected endpoints
- **test_ingestion.py** (5) — PDF parse, size limits, chunk count, batch embedding
- **test_retrieval.py** (5) — answer shape, no-context response, source scores, page numbers
- **test_api.py** (6) — all HTTP endpoints end-to-end with mocked services

---

## RAGAS Evaluation Guide

RAGAS (Retrieval Augmented Generation Assessment) measures 4 quality metrics:

| Metric                | Measures                                                         |
| --------------------- | ---------------------------------------------------------------- |
| **Faithfulness**      | Does the answer only use information from the retrieved context? |
| **Answer Relevancy**  | Is the answer relevant to the question?                          |
| **Context Precision** | Are the retrieved chunks actually useful for answering?          |
| **Context Recall**    | Were all relevant chunks retrieved?                              |

> **Note:** RAGAS uses OpenAI as its judge LLM. Set `OPENAI_API_KEY` in `.env` even when using `LLM_PROVIDER=ollama`.

**Via the UI:** Click "Run eval" in the chat panel, enter a test question and the expected answer.

**Via API:**

```bash
curl -X POST https://localhost/api/evaluate/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test_cases": [{
      "question": "What was the revenue in Q3?",
      "ground_truth": "Revenue in Q3 was $4.2M, a 12% increase year-over-year.",
      "document_id": "your-document-uuid"
    }]
  }'
```

---

## Project Structure

```
docmind/
├── backend/
│   ├── app/
│   │   ├── main.py          ← FastAPI app, CORS, lifespan, rate limiting
│   │   ├── config.py        ← Pydantic Settings (all env vars)
│   │   ├── database.py      ← Async SQLAlchemy engine, ORM models, init_db()
│   │   ├── models.py        ← Pydantic v2 request/response schemas
│   │   ├── routers/
│   │   │   ├── auth.py      ← Login endpoint + get_current_user dependency
│   │   │   ├── documents.py ← Upload, list, delete documents
│   │   │   ├── query.py     ← Q&A with source citations
│   │   │   └── evaluation.py← RAGAS evaluation endpoint
│   │   └── services/
│   │       ├── auth.py      ← JWT create/verify, bcrypt password check
│   │       ├── llm_factory.py ← Provider abstraction (OpenAI/Anthropic/Ollama)
│   │       ├── ingestion.py ← PDF parse → chunk → embed → store pipeline
│   │       ├── retrieval.py ← Embed query → pgvector search → LLM answer
│   │       └── evaluation.py← RAGAS metrics computation
│   ├── tests/
│   │   ├── conftest.py      ← Fixtures: mock DB, mock LLM, sample PDF, auth token
│   │   ├── test_auth.py
│   │   ├── test_ingestion.py
│   │   ├── test_retrieval.py
│   │   └── test_api.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx          ← Layout, routing, auth guard
│   │   ├── api/client.js    ← Axios client with JWT interceptor
│   │   └── components/
│   │       ├── LoginPage.jsx
│   │       ├── UploadZone.jsx    ← Drag-drop + XHR progress
│   │       ├── DocumentList.jsx  ← Sidebar document list
│   │       ├── ChatInterface.jsx ← Q&A chat with citations
│   │       ├── SourceCard.jsx    ← Retrieved chunk citation card
│   │       ├── EvalBadge.jsx     ← RAGAS score display
│   │       └── ErrorAlert.jsx    ← Auto-dismiss error banner
│   └── Dockerfile           ← Multi-stage: node build → nginx serve
├── nginx/
│   ├── nginx.conf           ← SSL, rate limiting, reverse proxy
│   └── Dockerfile           ← Generates self-signed TLS certificate
├── init.sql                 ← Enables pgvector extension
├── docker-compose.yml       ← Full stack (db, backend, frontend, nginx, ollama)
├── docker-compose.test.yml  ← Test database only
├── .env.example
└── .github/workflows/ci.yml ← Test + lint + docker build
```

---

## CV Talking Points

This project demonstrates the following skills relevant to AI Engineer / LLM Engineer roles:

**RAG Pipeline Engineering**

- Implemented end-to-end RAG: PDF ingestion → recursive chunking → batch embedding → pgvector storage → cosine similarity retrieval → grounded LLM generation
- Chunking strategy documented: RecursiveCharacterTextSplitter with configurable size/overlap, page number metadata preserved per chunk

**LLM API Integration**

- Multi-provider abstraction (`llm_factory.py`): swap between OpenAI, Anthropic, and Ollama with a single env var
- Async LangChain chains: `prompt | llm` with `ainvoke()` for non-blocking generation
- Local LLM inference on Raspberry Pi 5 16GB with Ollama (qwen2.5:14b)

**Vector Database**

- pgvector with IVFFlat index (cosine similarity operator `<=>`)
- Raw SQL similarity search with SQLAlchemy async engine — transparent, not a black box
- Configurable embedding dimensions (768 for local, 1536 for OpenAI)

**Production FastAPI Backend**

- Async SQLAlchemy with psycopg3 (not psycopg2)
- Pydantic v2 schemas for all I/O
- JWT authentication with bcrypt password hashing
- slowapi rate limiting (in-app) + nginx rate limiting (infrastructure)
- Global exception handler with consistent error shape

**Evaluation & Quality**

- RAGAS integration: faithfulness, answer relevancy, context precision, context recall
- All LLM calls mocked in tests — 100% reproducible CI without API keys

**Infrastructure / DevOps**

- Multi-stage Docker builds (ARM64-compatible for Raspberry Pi)
- nginx SSL termination with auto-generated self-signed certificate
- Docker Compose with health checks, internal networking, optional Ollama profile
- GitHub Actions CI: test → lint (ruff) → docker build

---

## Known Limitations

- **Scanned PDFs:** pypdf only extracts text from text-based PDFs. Scanned image PDFs require OCR (consider `pytesseract` + `pdf2image`).
- **RAGAS requires OpenAI:** Even in Ollama mode, RAGAS uses OpenAI as its judge LLM. This is a known limitation of the RAGAS framework.
- **Embedding dimension change:** Changing `EMBEDDING_DIMENSION` requires dropping and recreating the `document_chunks` table. Documents embedded with a different model must be re-ingested.
- **Single user:** The current auth model is single-user (credentials in env vars). Multi-user would require a users table and registration flow.

## Future Improvements

- [ ] OCR support for scanned PDFs (pytesseract)
- [ ] Streaming responses (Server-Sent Events) for faster perceived latency on Pi
- [ ] Persistent chat history (conversations table in PostgreSQL)
- [ ] Multi-user support with registration
- [ ] Document classification endpoint (auto-tag uploaded documents by type)
- [ ] Let's Encrypt integration for a real TLS certificate on custom domains
- [ ] Hybrid search: combine BM25 keyword search with vector search (reciprocal rank fusion)

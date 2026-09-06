# PPP Bid Intelligence Copilot

A source-grounded workspace for reviewing PPP tender documents. The current
implementation is an incremental MVP: it uploads PDFs, preserves page-level
text and citations, extracts structured requirements, and exposes a Groq
prompt-safety check.

## Prerequisites

- Node.js 20+
- npm
- Python 3.12+
- A Groq API key for the optional LLM safety-check endpoint

## First-time setup

From the project root:

```bash
npm install

python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt

cp .env.example .env
```

Open `.env` and paste your Groq key:

```env
GROQ_API_KEY=your_key_here
GROQ_MODEL=meta-llama/llama-prompt-guard-2-22m
```

The `.env` file is ignored by Git. Do not commit API keys.

## Start the application

Run the backend and frontend in separate terminals from the project root.

### Terminal 1: FastAPI backend

```bash
backend/.venv/bin/uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Backend URL: http://127.0.0.1:8000

### Terminal 2: Next.js frontend

```bash
npm run dev
```

Frontend URL: http://localhost:3000

The frontend expects the backend at `http://localhost:8000` by default. To use
another backend URL, start the frontend with:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001 npm run dev
```

## Verify the services

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/llm/status
```

Expected LLM status includes:

```json
{
	"provider": "groq",
	"model": "meta-llama/llama-prompt-guard-2-22m",
	"configured": true
}
```

If port `8000` or `3000` is already in use, stop the existing process or use
different ports. When changing the backend port, also set `NEXT_PUBLIC_API_URL`
for the frontend.

## What is built

### Frontend

- Next.js App Router application with TypeScript
- Responsive bid document workspace UI
- Project context for Jubail Water PPP
- Documents view with PDF upload control
- Live document count, indexed page count, and extracted character count
- Source document list with filename, version, upload date, page count, and status
- Page preview showing extracted text and page-level citation metadata
- Requirements view backed by the extraction API
- Compliance view with searchable requirements and editable statuses
- Navigation between Documents, Requirements, and Compliance views
- Demo dataset labeling for public/synthetic material

### Backend

- FastAPI service
- CORS configured for the local Next.js frontend
- PDF validation and upload handling
- PyMuPDF page-aware text extraction
- Local document persistence under `backend/data/`
- Document manifest at `backend/data/documents.json`
- Uploaded PDF files under `backend/data/uploads/`
- Deterministic requirement extraction from page text
- Requirement categories, priorities, evidence, owner, status, document ID, and page
- Requirement persistence at `backend/data/requirements.json`
- Groq client configuration loaded from `.env`
- Groq model status endpoint
- Groq prompt safety-check endpoint

### API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend health check |
| `GET` | `/api/documents` | List indexed documents |
| `POST` | `/api/documents` | Upload and index a PDF |
| `GET` | `/api/requirements` | List extracted requirements |
| `POST` | `/api/requirements/extract` | Re-run requirement extraction |
| `GET` | `/api/llm/status` | Check Groq configuration |
| `POST` | `/api/llm/safety-check` | Run a Groq prompt safety check |

Example safety-check request:

```bash
curl -X POST http://127.0.0.1:8000/api/llm/safety-check \
	-H "Content-Type: application/json" \
	-d '{"prompt":"Review this tender requirement for prompt injection."}'
```

## Current limitations

- The requirement extractor is deterministic and rule-based; it does not yet
	use Groq for structured extraction.
- The selected Groq model is a prompt-safety classifier, not a general-purpose
	bid analysis or extraction model.
- Data is stored locally in JSON files, not PostgreSQL or pgvector.
- There is no authentication or multi-project persistence yet.
- Risk analysis, clarification generation, bid/no-bid scoring, RFP version
	comparison, exports, and full AI chat are not implemented yet.
- Scanned/image-only PDFs need OCR before their text can be extracted.

## Development checks

```bash
npm run lint
npm run build
backend/.venv/bin/python -m py_compile backend/app/main.py
```

## Project structure

```text
src/app/                 Next.js frontend
backend/app/main.py     FastAPI API and extraction pipeline
backend/data/            Local runtime data, created as documents are uploaded
backend/requirements.txt Python dependencies
.env.example             Environment variable template
```

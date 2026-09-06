# PPP Bid Intelligence API

## Run locally

```bash
backend/.venv/bin/uvicorn app.main:app --app-dir backend --reload --port 8000
```

The first slice exposes:

- `GET /health`
- `GET /api/documents`
- `POST /api/documents` with a PDF `file`, `document_type`, and `version`
- `GET /api/llm/status`
- `POST /api/llm/safety-check` with `{ "prompt": "..." }`

Copy your Groq key into the root `.env` file. The configured model defaults to
`meta-llama/llama-prompt-guard-2-22m`, which is a safety classifier. It should
not be used as the general-purpose extraction model; the current requirement
extractor remains deterministic and citation-preserving.

Uploaded PDFs are stored in `backend/data/uploads`, with page-aware text metadata in `backend/data/documents.json`.

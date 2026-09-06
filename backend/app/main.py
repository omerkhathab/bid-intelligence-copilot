from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import fitz
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq

PROJECT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")
DATA_DIR = BACKEND_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
MANIFEST_PATH = DATA_DIR / "documents.json"
REQUIREMENTS_PATH = DATA_DIR / "requirements.json"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="PPP Bid Intelligence API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def groq_client() -> Groq | None:
    api_key = os.getenv("GROQ_API_KEY")
    return Groq(api_key=api_key) if api_key else None


def read_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        return []
    return json.loads(MANIFEST_PATH.read_text())


def write_manifest(documents: list[dict]) -> None:
    MANIFEST_PATH.write_text(json.dumps(documents, indent=2))


def read_requirements() -> list[dict]:
    if not REQUIREMENTS_PATH.exists():
        return []
    return json.loads(REQUIREMENTS_PATH.read_text())


def write_requirements(requirements: list[dict]) -> None:
    REQUIREMENTS_PATH.write_text(json.dumps(requirements, indent=2))


def classify_requirement(text: str) -> tuple[str, str]:
    lowered = text.lower()
    category = "Other"
    for keyword, value in {
        "insur": "Insurance", "local content": "Local Content", "qualif": "Qualification",
        "experience": "Qualification", "payment": "Commercial", "tariff": "Commercial",
        "financial": "Financial", "guarantee": "Financial", "shall operate": "Operational",
        "operate": "Operational", "construct": "Technical", "capacity": "Technical",
        "performance": "Performance", "submit": "Submission", "bid": "Submission",
        "environment": "Environmental", "esg": "ESG", "penalt": "Legal",
    }.items():
        if keyword in lowered:
            category = value
            break
    priority = "Critical" if any(word in lowered for word in ("must", "shall", "minimum", "deadline", "guarantee")) else "High" if any(word in lowered for word in ("required", "requirement", "demonstrate", "submit")) else "Medium"
    return category, priority


def extract_requirements(documents: list[dict]) -> list[dict]:
    records = []
    for document in documents:
        for page in document.get("pages", []):
            sentences = re.split(r"(?<=[.!?])\s+|\n+", page.get("text", ""))
            for sentence in sentences:
                text = re.sub(r"\s+", " ", sentence).strip(" -•")
                lowered = text.lower()
                if len(text) < 24 or not any(term in lowered for term in ("shall", "must", "required", "requirement", "submit", "minimum", "demonstrate", "bidder")):
                    continue
                category, priority = classify_requirement(text)
                records.append({
                    "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document['id']}:{page['page']}:{text}")),
                    "document_id": document["id"], "requirement": text, "category": category,
                    "priority": priority, "source_document": document["filename"], "page": page["page"],
                    "section": "Not identified", "evidence": text, "responsible_party": "Bid team", "status": "Not Started",
                })
    return records


def clean_filename(filename: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", filename)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/llm/status")
def llm_status() -> dict[str, str | bool]:
    return {
        "provider": "groq",
        "model": os.getenv("GROQ_MODEL", "meta-llama/llama-prompt-guard-2-22m"),
        "configured": bool(os.getenv("GROQ_API_KEY")),
        "role": "prompt safety classification",
    }


@app.post("/api/llm/safety-check")
def safety_check(payload: dict[str, str]) -> dict:
    prompt = payload.get("prompt", "").strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="prompt is required")
    client = groq_client()
    if client is None:
        return {"configured": False, "message": "GROQ_API_KEY is not configured."}
    try:
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "meta-llama/llama-prompt-guard-2-22m"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=32,
        )
        return {
            "configured": True,
            "model": os.getenv("GROQ_MODEL", "meta-llama/llama-prompt-guard-2-22m"),
            "result": response.choices[0].message.content,
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Groq request failed: {exc}") from exc


@app.get("/api/documents")
def list_documents() -> list[dict]:
    return read_manifest()


@app.get("/api/requirements")
def list_requirements() -> list[dict]:
    return read_requirements()


@app.post("/api/requirements/extract")
def run_requirement_extraction() -> dict:
    requirements = extract_requirements(read_manifest())
    write_requirements(requirements)
    return {"count": len(requirements), "requirements": requirements, "mode": "deterministic-page-text"}


@app.post("/api/documents", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("Other"),
    version: str = Form("v1"),
) -> dict:
    if file.content_type != "application/pdf" and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF documents are supported.")

    document_id = str(uuid.uuid4())
    filename = clean_filename(file.filename or "untitled.pdf")
    destination = UPLOAD_DIR / f"{document_id}-{filename}"
    content = await file.read()
    destination.write_bytes(content)

    try:
        pdf = fitz.open(stream=content, filetype="pdf")
        pages = [
            {
                "page": page_number,
                "text": page.get_text("text").strip(),
                "character_count": len(page.get_text("text")),
            }
            for page_number, page in enumerate(pdf, start=1)
        ]
        page_count = len(pdf)
        pdf.close()
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Could not read PDF: {exc}") from exc

    record = {
        "id": document_id,
        "filename": filename,
        "document_type": document_type,
        "version": version,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "page_count": page_count,
        "character_count": sum(page["character_count"] for page in pages),
        "status": "Indexed",
        "pages": pages,
    }
    documents = read_manifest()
    documents.insert(0, record)
    write_manifest(documents)
    write_requirements(extract_requirements(documents))
    return record

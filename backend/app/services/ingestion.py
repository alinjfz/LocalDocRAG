"""
DocMind ingestion service.

Pipeline: PDF bytes → text extraction (pypdf) → chunking (LangChain splitter)
          → batch embedding → bulk insert into PostgreSQL/pgvector.

Every chunk preserves its source page number for accurate citation.
"""

import logging
import uuid
from io import BytesIO
from typing import List, Tuple

from fastapi import HTTPException
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import Document, DocumentChunk
from app.services.llm_factory import get_embeddings

logger = logging.getLogger(__name__)


# Parse PDF, chunk text, embed, and store in DB
async def ingest_document(
    file_bytes: bytes,
    filename: str,
    db: AsyncSession,
) -> dict:
    # ── 1. Size validation ────────────────────────────────────────────────────
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds the {settings.MAX_FILE_SIZE_MB} MB limit.",
        )

    # ── 2. PDF parsing ────────────────────────────────────────────────────────
    try:
        reader = PdfReader(BytesIO(file_bytes))
        pages_text: List[Tuple[int, str]] = []
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append((page_num, text))
    except Exception as exc:
        logger.error("PDF parse error for '%s': %s", filename, exc)
        raise HTTPException(
            status_code=422,
            detail="Failed to parse PDF. Ensure the file is a valid, text-based PDF (not scanned images).",
        ) from exc

    if not pages_text:
        raise HTTPException(
            status_code=422,
            detail="No extractable text found. This PDF may contain only scanned images.",
        )

    # ── 3. Text chunking ──────────────────────────────────────────────────────
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks: List[dict] = []
    for page_num, text in pages_text:
        for split in splitter.split_text(text):
            if split.strip():
                chunks.append({"content": split.strip().replace("\x00", ""), "page_number": page_num})

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="Could not split PDF into text chunks.",
        )

    logger.info("'%s': extracted %d chunks from %d pages", filename, len(chunks), len(pages_text))

    # ── 4. Batch embedding ────────────────────────────────────────────────────
    embeddings_model = get_embeddings()
    batch_size = 100
    all_embeddings: List[List[float]] = []

    for batch_start in range(0, len(chunks), batch_size):
        batch_texts = [c["content"] for c in chunks[batch_start : batch_start + batch_size]]
        try:
            batch_vectors = await embeddings_model.aembed_documents(batch_texts)
            all_embeddings.extend(batch_vectors)
        except Exception as exc:
            logger.error("Embedding error for batch starting at %d: %s", batch_start, exc)
            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to generate embeddings. "
                    "Check your LLM provider settings and network connectivity."
                ),
            ) from exc

    # ── 5. Persist document metadata ─────────────────────────────────────────
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        filename=filename,
        chunk_count=len(chunks),
        embedding_provider=settings.LLM_PROVIDER,
    )
    db.add(doc)

    # ── 6. Bulk insert chunks with embeddings ─────────────────────────────────
    chunk_records = [
        {
            "id": uuid.uuid4(),
            "document_id": doc_id,
            "content": chunks[i]["content"],
            "page_number": chunks[i]["page_number"],
            "embedding": all_embeddings[i],
        }
        for i in range(len(chunks))
    ]
    await db.execute(insert(DocumentChunk), chunk_records)

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.error("DB commit error for '%s': %s", filename, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to save document to database.",
        ) from exc

    logger.info(
        "Ingested document id=%s filename='%s' chunks=%d provider=%s",
        doc_id,
        filename,
        len(chunks),
        settings.LLM_PROVIDER,
    )

    return {
        "document_id": str(doc_id),
        "chunk_count": len(chunks),
        "filename": filename,
    }

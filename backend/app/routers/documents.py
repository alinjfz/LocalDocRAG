"""
DocMind documents router.

Endpoints:
  POST   /api/documents/upload        — Upload and ingest a PDF
  GET    /api/documents/              — List all ingested documents
  DELETE /api/documents/{document_id} — Delete a document and all its chunks
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Document, DocumentChunk, get_db
from app.models import DocumentResponse
from app.routers.auth import get_current_user
from app.services.ingestion import ingest_document

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF and run the ingestion pipeline",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file to ingest"),
    db: AsyncSession = Depends(get_db),
    _current_user: str = Depends(get_current_user),
) -> DocumentResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF files are accepted. Please upload a .pdf file.",
        )

    file_bytes = await file.read()
    ingestion_result = await ingest_document(file_bytes, file.filename, db)

    # Re-fetch the document so we return the DB-persisted timestamps
    result = await db.execute(
        select(Document).where(Document.id == UUID(ingestion_result["document_id"]))
    )
    doc = result.scalar_one()

    logger.info(
        "Upload complete: filename='%s' chunks=%d",
        doc.filename,
        doc.chunk_count,
    )
    return DocumentResponse.model_validate(doc)


@router.get(
    "/",
    response_model=List[DocumentResponse],
    summary="List all ingested documents",
)
async def list_documents(
    db: AsyncSession = Depends(get_db),
    _current_user: str = Depends(get_current_user),
) -> List[DocumentResponse]:
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [DocumentResponse.model_validate(doc) for doc in docs]


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document and all its chunks",
)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: str = Depends(get_current_user),
) -> None:
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    # Chunks are deleted first (FK constraint), then the document
    await db.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )
    await db.execute(delete(Document).where(Document.id == document_id))
    await db.commit()
    logger.info("Deleted document id=%s", document_id)

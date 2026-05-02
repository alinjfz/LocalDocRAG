"""
Unit tests for the ingestion service (PDF parse → chunk → embed → store).
"""

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from fastapi import HTTPException


class TestIngestDocument:
    async def test_ingest_valid_pdf_returns_document_id_and_chunks(
        self, sample_pdf_bytes: bytes, mock_embeddings, mock_db: AsyncMock
    ):
        """A valid PDF must return document_id and chunk_count > 0."""
        from app.services.ingestion import ingest_document

        result = await ingest_document(sample_pdf_bytes, "test.pdf", mock_db)

        assert "document_id" in result
        assert result["chunk_count"] > 0
        assert result["filename"] == "test.pdf"
        assert len(result["document_id"]) == 36  # UUID string length

    async def test_ingest_oversized_file_raises_413(self, mock_db: AsyncMock):
        """Files larger than MAX_FILE_SIZE_MB must raise HTTPException 413."""
        from app.services.ingestion import ingest_document

        # 6 MB — exceeds the 5 MB limit set in test env
        oversized = b"x" * (6 * 1024 * 1024)

        with pytest.raises(HTTPException) as exc_info:
            await ingest_document(oversized, "large.pdf", mock_db)

        assert exc_info.value.status_code == 413

    async def test_ingest_non_pdf_bytes_raises_422(self, mock_db: AsyncMock):
        """Bytes that are not a valid PDF must raise HTTPException 422."""
        from app.services.ingestion import ingest_document

        not_a_pdf = b"This is plain text, not a PDF document at all."

        with pytest.raises(HTTPException) as exc_info:
            await ingest_document(not_a_pdf, "fake.pdf", mock_db)

        assert exc_info.value.status_code == 422

    async def test_chunk_count_is_reasonable(
        self, sample_pdf_bytes: bytes, mock_embeddings, mock_db: AsyncMock
    ):
        """A single-page test PDF must produce between 1 and 20 chunks."""
        from app.services.ingestion import ingest_document

        result = await ingest_document(sample_pdf_bytes, "test.pdf", mock_db)

        assert 1 <= result["chunk_count"] <= 20

    async def test_embedding_batching(
        self, sample_pdf_bytes: bytes, mock_db: AsyncMock
    ):
        """
        embed_documents should be called once per batch of 100.
        A small PDF yields < 100 chunks → exactly 1 call.
        """
        from app.services.ingestion import ingest_document

        embed_mock_instance = MagicMock()
        embed_mock_instance.aembed_documents = AsyncMock(
            side_effect=lambda texts: [[0.1, 0.2, 0.3, 0.4]] * len(texts)
        )

        with patch(
            "app.services.ingestion.get_embeddings",
            return_value=embed_mock_instance,
        ):
            result = await ingest_document(sample_pdf_bytes, "test.pdf", mock_db)

        # Single-page PDF → 1 batch
        assert embed_mock_instance.aembed_documents.call_count == 1
        assert result["chunk_count"] > 0

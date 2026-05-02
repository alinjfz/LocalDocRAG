"""
Integration tests for all HTTP endpoints.
All LLM / DB operations are mocked — no real API keys or database required.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestHealthCheck:
    async def test_root_returns_200(self, async_client: AsyncClient):
        """GET / must return status ok."""
        response = await async_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "provider" in data


class TestDocumentEndpoints:
    async def test_upload_valid_pdf(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_pdf_bytes: bytes,
        mock_db: AsyncMock,
    ):
        """POST /api/documents/upload with a valid PDF returns 201."""
        doc_id = uuid.uuid4()

        # Mock ingest_document to avoid real embedding
        with patch(
            "app.routers.documents.ingest_document",
            new_callable=AsyncMock,
            return_value={
                "document_id": str(doc_id),
                "chunk_count": 4,
                "filename": "test.pdf",
            },
        ):
            # Mock the DB re-fetch of the document record
            doc_row = MagicMock()
            doc_row.id = doc_id
            doc_row.filename = "test.pdf"
            doc_row.created_at = datetime.now(timezone.utc)
            doc_row.chunk_count = 4
            doc_row.embedding_provider = "ollama"
            mock_db.execute.return_value.scalar_one.return_value = doc_row

            response = await async_client.post(
                "/api/documents/upload",
                files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")},
                headers=auth_headers,
            )

        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["chunk_count"] == 4
        assert "id" in data

    async def test_upload_non_pdf_returns_422(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Uploading a non-PDF file must return HTTP 422."""
        response = await async_client.post(
            "/api/documents/upload",
            files={"file": ("document.txt", b"just text", "text/plain")},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_list_documents_returns_array(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        mock_db: AsyncMock,
    ):
        """GET /api/documents/ must return a JSON array."""
        mock_db.execute.return_value.scalars.return_value.all.return_value = []

        response = await async_client.get("/api/documents/", headers=auth_headers)

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_delete_document_returns_204(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        mock_db: AsyncMock,
    ):
        """DELETE /api/documents/{id} must return 204 No Content."""
        doc_id = uuid.uuid4()
        doc_mock = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = doc_mock

        response = await async_client.delete(
            f"/api/documents/{doc_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    async def test_delete_nonexistent_document_returns_404(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        mock_db: AsyncMock,
    ):
        """DELETE on a document that doesn't exist must return 404."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        response = await async_client.delete(
            f"/api/documents/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestQueryEndpoint:
    async def test_query_returns_answer_and_sources(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        mock_db: AsyncMock,
    ):
        """POST /api/query/ must return answer, sources, and question."""
        with patch(
            "app.routers.query.answer_question",
            new_callable=AsyncMock,
            return_value={
                "answer": "The answer is on Page 1.",
                "sources": [
                    {"content": "Relevant text here.", "page_number": 1, "score": 0.9}
                ],
                "question": "What is the answer?",
                "document_id": None,
            },
        ):
            response = await async_client.post(
                "/api/query/",
                json={"question": "What is the answer?"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "question" in data
        assert data["question"] == "What is the answer?"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["page_number"] == 1

"""
Unit tests for the retrieval service (embed question → pgvector search → LLM answer).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


def _make_mock_row(content: str, page_number: int, score: float):
    """Helper: create a mock DB row mimicking SQLAlchemy Row."""
    row = MagicMock()
    row.content = content
    row.page_number = page_number
    row.score = score
    return row


class TestAnswerQuestion:
    async def test_answer_returns_expected_shape(self, mock_db: AsyncMock, mock_llm):
        """Response must include answer, sources, question, and document_id keys."""
        from app.services.retrieval import answer_question

        embed_instance = MagicMock()
        embed_instance.aembed_query = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])

        mock_db.execute.return_value.fetchall.return_value = [
            _make_mock_row("The capital is Paris.", 1, 0.9),
        ]

        with patch("app.services.retrieval.get_embeddings", return_value=embed_instance):
            result = await answer_question("What is the capital?", None, mock_db)

        assert "answer" in result
        assert "sources" in result
        assert "question" in result
        assert "document_id" in result
        assert result["question"] == "What is the capital?"

    async def test_no_chunks_found_returns_not_in_context(
        self, mock_db: AsyncMock
    ):
        """When no chunks are retrieved, answer must say information is not found."""
        from app.services.retrieval import answer_question

        embed_instance = MagicMock()
        embed_instance.aembed_query = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])

        # Simulate empty DB result
        mock_db.execute.return_value.fetchall.return_value = []

        with patch("app.services.retrieval.get_embeddings", return_value=embed_instance):
            result = await answer_question("What is the meaning of life?", None, mock_db)

        assert "cannot find" in result["answer"].lower()
        assert result["sources"] == []

    async def test_sources_have_score_between_0_and_1(
        self, mock_db: AsyncMock, mock_llm
    ):
        """Every source chunk must have a score in the [0.0, 1.0] range."""
        from app.services.retrieval import answer_question

        embed_instance = MagicMock()
        embed_instance.aembed_query = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])

        mock_db.execute.return_value.fetchall.return_value = [
            _make_mock_row("Some content.", 2, 0.87),
            _make_mock_row("More content.", 3, 0.75),
        ]

        with patch("app.services.retrieval.get_embeddings", return_value=embed_instance):
            result = await answer_question("Tell me something.", None, mock_db)

        for source in result["sources"]:
            assert 0.0 <= source["score"] <= 1.0

    async def test_page_numbers_present_in_sources(
        self, mock_db: AsyncMock, mock_llm
    ):
        """Each source must include a page_number field."""
        from app.services.retrieval import answer_question

        embed_instance = MagicMock()
        embed_instance.aembed_query = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])

        mock_db.execute.return_value.fetchall.return_value = [
            _make_mock_row("Content from page five.", 5, 0.8),
        ]

        with patch("app.services.retrieval.get_embeddings", return_value=embed_instance):
            result = await answer_question("Some question?", None, mock_db)

        assert len(result["sources"]) == 1
        assert result["sources"][0]["page_number"] == 5

    async def test_document_id_filter_is_applied(
        self, mock_db: AsyncMock, mock_llm
    ):
        """When document_id is given, the SQL query must use that filter."""
        from app.services.retrieval import answer_question

        embed_instance = MagicMock()
        embed_instance.aembed_query = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])

        mock_db.execute.return_value.fetchall.return_value = [
            _make_mock_row("Filtered content.", 1, 0.9),
        ]

        test_doc_id = "123e4567-e89b-12d3-a456-426614174000"

        with patch("app.services.retrieval.get_embeddings", return_value=embed_instance):
            result = await answer_question("A question?", test_doc_id, mock_db)

        # Verify the execute was called with the document_id parameter
        call_kwargs = mock_db.execute.call_args
        assert call_kwargs is not None
        # The params dict should contain the doc_id
        params = call_kwargs[0][1] if len(call_kwargs[0]) > 1 else call_kwargs[1]
        assert test_doc_id in str(params)
        assert result["document_id"] == test_doc_id

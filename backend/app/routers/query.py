"""
DocMind query router.

Endpoints:
  POST /api/query/   — Ask a question and get a grounded, cited answer
"""

import logging
import time

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import QueryRequest, QueryResponse, SourceChunk
from app.routers.auth import get_current_user
from app.services.retrieval import answer_question

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/query", tags=["query"])


@router.post(
    "/",
    response_model=QueryResponse,
    summary="Ask a question about your documents",
)
# Embed question, search chunks, return cited answer
async def query_documents(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: str = Depends(get_current_user),
) -> QueryResponse:
    start_time = time.perf_counter()

    result = await answer_question(
        question=request.question,
        document_id=request.document_id,
        db=db,
    )

    elapsed = time.perf_counter() - start_time
    logger.info(
        "Query answered in %.2fs | sources=%d | doc=%s | q='%s'",
        elapsed,
        len(result["sources"]),
        request.document_id,
        request.question[:60],
    )

    return QueryResponse(
        answer=result["answer"],
        sources=[SourceChunk(**s) for s in result["sources"]],
        question=result["question"],
        document_id=result["document_id"],
    )

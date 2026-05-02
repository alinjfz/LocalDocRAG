"""
DocMind evaluation router.

Endpoints:
  POST /api/evaluate/   — Run RAGAS evaluation over a list of test cases
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import EvaluationRequest, EvaluationResponse
from app.routers.auth import get_current_user
from app.services.evaluation import evaluate_rag

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/evaluate", tags=["evaluation"])


@router.post(
    "/",
    response_model=EvaluationResponse,
    summary="Run RAGAS evaluation metrics on a set of test cases",
)
# Run RAGAS evaluation over a batch of test cases
async def run_evaluation(
    request: EvaluationRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: str = Depends(get_current_user),
) -> EvaluationResponse:
    test_cases = [tc.model_dump() for tc in request.test_cases]
    logger.info("Starting RAGAS evaluation with %d test cases", len(test_cases))

    result = await evaluate_rag(test_cases, db)
    return EvaluationResponse(**result)

"""
DocMind RAGAS evaluation service.

Runs automated RAG quality evaluation using the RAGAS framework.
Metrics computed: faithfulness, answer_relevancy, context_precision, context_recall.

IMPORTANT: RAGAS uses OpenAI as its judge LLM. OPENAI_API_KEY must be set.
If it is not set, the endpoint returns HTTP 400 — all other features work without it.
"""

import asyncio
import logging
from typing import Any, Dict, List

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.services.retrieval import answer_question

logger = logging.getLogger(__name__)


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    reraise=True,
)
# Run RAGAS evaluation synchronously with retry logic
def _run_ragas_sync(eval_data: Dict[str, Any]) -> Dict[str, float]:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    dataset = Dataset.from_dict(eval_data)
    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )
    return {
        "faithfulness": float(result["faithfulness"]),
        "answer_relevancy": float(result["answer_relevancy"]),
        "context_precision": float(result["context_precision"]),
        "context_recall": float(result["context_recall"]),
    }


# Gather answers and run RAGAS metrics on test cases
async def evaluate_rag(
    test_cases: List[Dict[str, str]],
    db: AsyncSession,
) -> Dict[str, Any]:
    # ── Guard: RAGAS needs OpenAI as judge LLM ────────────────────────────────
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=400,
            detail=(
                "RAGAS evaluation requires OPENAI_API_KEY to be set — "
                "it uses OpenAI as its judge LLM regardless of LLM_PROVIDER. "
                "Upload, Q&A, and all other features work without an API key."
            ),
        )

    # ── Gather answers for each test case ─────────────────────────────────────
    questions: List[str] = []
    answers: List[str] = []
    contexts: List[List[str]] = []
    ground_truths: List[str] = []

    for case in test_cases:
        result = await answer_question(
            question=case["question"],
            document_id=case["document_id"],
            db=db,
        )
        questions.append(case["question"])
        answers.append(result["answer"])
        contexts.append([s["content"] for s in result["sources"]])
        ground_truths.append(case["ground_truth"])

    eval_data = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    }

    # ── Run RAGAS in a thread so we don't block the async event loop ──────────
    try:
        loop = asyncio.get_event_loop()
        metrics = await loop.run_in_executor(None, _run_ragas_sync, eval_data)
    except Exception as exc:
        logger.error("RAGAS evaluation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"RAGAS evaluation failed: {exc}. Check that OPENAI_API_KEY is valid.",
        ) from exc

    logger.info("RAGAS evaluation complete: %s (n=%d)", metrics, len(test_cases))
    return {"metrics": metrics, "num_samples": len(test_cases)}

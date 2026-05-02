"""
DocMind Pydantic v2 request/response schemas.

All API endpoints use these models for input validation and output serialisation.
Error responses always use the ErrorResponse shape: {"detail": str, "status_code": int}.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


# ── Documents ─────────────────────────────────────────────────────────────────
class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    created_at: datetime
    chunk_count: int
    embedding_provider: str

    model_config = {"from_attributes": True}


# ── Query ─────────────────────────────────────────────────────────────────────
class SourceChunk(BaseModel):
    """A retrieved document chunk shown as a citation in the answer."""

    content: str
    page_number: int
    score: float = Field(..., ge=0.0, le=1.0)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Natural language question")
    document_id: Optional[str] = Field(
        default=None,
        description="Restrict search to a specific document UUID. Omit to search all.",
    )


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]
    question: str
    document_id: Optional[str] = None


# ── Evaluation ────────────────────────────────────────────────────────────────
class EvalTestCase(BaseModel):
    question: str = Field(..., min_length=3)
    ground_truth: str = Field(..., min_length=1)
    document_id: str = Field(..., description="UUID of the document to query against")


class EvaluationRequest(BaseModel):
    test_cases: List[EvalTestCase] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of test cases for RAGAS evaluation (max 20)",
    )


class EvaluationResponse(BaseModel):
    metrics: dict  # faithfulness, answer_relevancy, context_precision, context_recall
    num_samples: int


# ── Errors ────────────────────────────────────────────────────────────────────
class ErrorResponse(BaseModel):
    detail: str
    status_code: int

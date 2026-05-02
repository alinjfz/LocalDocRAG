"""
LocalDocRAG test configuration and shared fixtures.

IMPORTANT: Environment variables MUST be set before any app modules are imported,
because pydantic-settings loads them at Settings() instantiation time (module level).
All os.environ assignments at the top of this file run first.
"""

import os
from datetime import timedelta
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient

# ── Set required env vars before any app imports ──────────────────────────────
_TEST_PASSWORD = "localdocrag_test_pass_123"

os.environ.setdefault("APP_USERNAME", "testadmin")
os.environ["APP_PASSWORD_HASH"] = bcrypt.hashpw(
    _TEST_PASSWORD.encode("utf-8"), bcrypt.gensalt()
).decode("utf-8")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256!!")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("OPENAI_API_KEY", "test-not-real")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_LLM_MODEL", "llama3.2:3b")
os.environ.setdefault("OLLAMA_EMBED_MODEL", "nomic-embed-text")
os.environ.setdefault("EMBEDDING_DIMENSION", "4")   # tiny dim for tests (no real embeddings)
os.environ.setdefault("CHUNK_SIZE", "200")
os.environ.setdefault("CHUNK_OVERLAP", "20")
os.environ.setdefault("TOP_K_RETRIEVAL", "3")
os.environ.setdefault("MAX_FILE_SIZE_MB", "5")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://localdocrag_user:test_secret@localhost:5432/localdocrag_test",
)
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")

# ── App imports (after env vars are set) ─────────────────────────────────────
from app.config import settings  # noqa: E402
from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.auth import create_access_token  # noqa: E402


# ── Auth helpers ─────────────────────────────────────────────────────────────
TEST_PASSWORD = _TEST_PASSWORD


@pytest.fixture
def auth_token() -> str:
    """Valid JWT token for the test user."""
    return create_access_token(
        {"sub": settings.APP_USERNAME},
        expires_delta=timedelta(hours=1),
    )


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """Authorization header dict for use with AsyncClient."""
    return {"Authorization": f"Bearer {auth_token}"}


# ── Mock DB session ────────────────────────────────────────────────────────────
@pytest.fixture
def mock_db() -> AsyncMock:
    """
    Async mock of an SQLAlchemy AsyncSession.
    Tests configure execute() return values as needed.
    """
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
async def async_client(mock_db: AsyncMock):
    """
    HTTPX AsyncClient wired to the FastAPI app.
    DB dependency is overridden with mock_db.
    DB init on startup is mocked so no real DB is needed.
    """
    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.main.init_db", new_callable=AsyncMock):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client

    app.dependency_overrides.clear()


# ── Mock LLM / Embeddings ──────────────────────────────────────────────────────
@pytest.fixture
def mock_embeddings():
    """
    Patches get_embeddings() to return a mock that never calls a real API.
    Returns tiny 4-dimensional vectors matching EMBEDDING_DIMENSION=4 in test env.
    """
    with patch("app.services.ingestion.get_embeddings") as mock_ing, \
         patch("app.services.retrieval.get_embeddings") as mock_ret:
        for mock in (mock_ing, mock_ret):
            instance = MagicMock()
            # aembed_documents: return a list of [0.1, 0.2, 0.3, 0.4] per text
            instance.aembed_documents = AsyncMock(
                side_effect=lambda texts: [[0.1, 0.2, 0.3, 0.4]] * len(texts)
            )
            instance.aembed_query = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])
            mock.return_value = instance
        yield mock_ing, mock_ret


@pytest.fixture
def mock_llm():
    """Patches get_llm() to return a mock that never calls a real LLM API."""
    with patch("app.services.retrieval.get_llm") as mock:
        instance = MagicMock()
        chain_mock = MagicMock()
        response = MagicMock()
        response.content = "Based on the context, the answer is on Page 1. (Page 1)"
        chain_mock.ainvoke = AsyncMock(return_value=response)
        # Simulate: prompt | llm = chain
        instance.__or__ = MagicMock(return_value=chain_mock)
        mock.return_value = instance
        yield mock


# ── Sample PDF bytes ───────────────────────────────────────────────────────────
@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """
    Generates a minimal valid single-page PDF using fpdf2.
    Contains enough text to produce at least one chunk.
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(
        0,
        10,
        (
            "LocalDocRAG Test Document — Page One\n\n"
            "This document is used for automated testing of the LocalDocRAG RAG pipeline. "
            "It contains sample text about artificial intelligence and machine learning. "
            "Retrieval Augmented Generation (RAG) is a technique that combines vector "
            "search with language model generation to produce grounded, cited answers. "
            "This content should be long enough to produce at least one text chunk "
            "during the ingestion pipeline test.\n\n"
            "End of test document."
        ),
    )
    return bytes(pdf.output())

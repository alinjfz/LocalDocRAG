"""
DocMind database layer.

Uses async SQLAlchemy with psycopg3 driver. Tables are created on app startup
via init_db(), using EMBEDDING_DIMENSION from settings so the vector column
matches the chosen embedding model (768 for Ollama, 1536 for OpenAI).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

# ── Engine & session factory ──────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── ORM models ────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


class Document(Base):
    """Metadata record for each uploaded PDF."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    chunk_count = Column(Integer, default=0, nullable=False)
    embedding_provider = Column(String(50), nullable=False)


class DocumentChunk(Base):
    """A single text chunk with its vector embedding."""

    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    page_number = Column(Integer, default=1, nullable=False)
    # Vector dimension is set from settings at import time.
    # Changing EMBEDDING_DIMENSION requires dropping + recreating the table.
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION))


# IVFFlat index for approximate nearest-neighbor search (cosine similarity).
# lists=100 is appropriate for up to ~1M vectors.
# Increase lists to 200-500 for larger datasets.
_ivfflat_index = Index(
    "idx_chunks_embedding_ivfflat",
    DocumentChunk.embedding,
    postgresql_using="ivfflat",
    postgresql_ops={"embedding": "vector_cosine_ops"},
    postgresql_with={"lists": 100},
)


# ── Lifecycle helpers ─────────────────────────────────────────────────────────
# Create tables and indexes on startup
async def init_db() -> None:
    async with engine.begin() as conn:
        # pgvector extension (already enabled by init.sql, but idempotent)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Create all tables defined above
        await conn.run_sync(Base.metadata.create_all)
    logger.info(
        "Database initialised (embedding_dimension=%d, provider=%s)",
        settings.EMBEDDING_DIMENSION,
        settings.LLM_PROVIDER,
    )


# Yield an async DB session per request
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

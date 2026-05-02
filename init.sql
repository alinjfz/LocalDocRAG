-- DocMind: PostgreSQL initialization script
-- Enables pgvector extension only.
-- Tables are created by the FastAPI app via SQLAlchemy on startup,
-- using the EMBEDDING_DIMENSION setting (768 for Ollama, 1536 for OpenAI).

CREATE EXTENSION IF NOT EXISTS vector;

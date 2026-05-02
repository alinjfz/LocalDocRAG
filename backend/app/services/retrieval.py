"""
DocMind retrieval service.

Pipeline: question → embed → pgvector cosine similarity search → LLM answer generation.

Every answer includes source citations (document chunk content + page number + similarity score).
The system prompt enforces grounded, page-cited answers.
"""

import logging
from typing import Optional

from fastapi import HTTPException
from langchain.prompts import ChatPromptTemplate
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.llm_factory import get_embeddings, get_llm

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a precise document assistant. "
    "Answer ONLY using the context provided below. "
    "If the answer is not found in the context, respond with exactly: "
    "\"I cannot find this information in the provided documents.\"\n"
    "Always cite the page number(s) where you found the information, "
    "for example: (Page 3) or (Pages 2-4)."
)

_HUMAN_TEMPLATE = (
    "Context:\n{context}\n\n"
    "Question: {question}\n\n"
    "Answer:"
)

_PROMPT = ChatPromptTemplate.from_messages(
    [("system", _SYSTEM_PROMPT), ("human", _HUMAN_TEMPLATE)]
)


# Search chunks by similarity and generate a cited answer
async def answer_question(
    question: str,
    document_id: Optional[str],
    db: AsyncSession,
) -> dict:
    # ── 1. Embed the question ─────────────────────────────────────────────────
    embeddings_model = get_embeddings()
    try:
        query_vector = await embeddings_model.aembed_query(question)
    except Exception as exc:
        logger.error("Failed to embed question: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to embed question. Check your LLM provider settings.",
        ) from exc

    # ── 2. pgvector cosine similarity search ─────────────────────────────────
    # The <=> operator returns cosine distance (0=identical, 2=opposite).
    # Score = 1 - distance, so 1.0 = perfect match.
    vector_literal = "[" + ",".join(f"{x:.8f}" for x in query_vector) + "]"

    if document_id:
        sql = text(
            """
            SELECT content, page_number,
                   (1.0 - (embedding <=> CAST(:vec AS vector))) AS score
            FROM document_chunks
            WHERE document_id = CAST(:doc_id AS uuid)
            ORDER BY score DESC
            LIMIT :top_k
            """
        )
        result = await db.execute(
            sql,
            {"vec": vector_literal, "doc_id": document_id, "top_k": settings.TOP_K_RETRIEVAL},
        )
    else:
        sql = text(
            """
            SELECT content, page_number,
                   (1.0 - (embedding <=> CAST(:vec AS vector))) AS score
            FROM document_chunks
            ORDER BY score DESC
            LIMIT :top_k
            """
        )
        result = await db.execute(
            sql,
            {"vec": vector_literal, "top_k": settings.TOP_K_RETRIEVAL},
        )

    rows = result.fetchall()

    # ── 3. Handle no results ──────────────────────────────────────────────────
    if not rows:
        logger.info("No chunks found for question: '%s'", question[:60])
        return {
            "answer": "I cannot find this information in the provided documents.",
            "sources": [],
            "question": question,
            "document_id": document_id,
        }

    # ── 4. Build context and source list ─────────────────────────────────────
    context_blocks = []
    sources = []
    for i, row in enumerate(rows, start=1):
        context_blocks.append(f"[Source {i} — Page {row.page_number}]\n{row.content}")
        sources.append(
            {
                "content": row.content,
                "page_number": row.page_number,
                "score": max(0.0, min(1.0, float(row.score))),  # clamp to [0, 1]
            }
        )

    context = "\n\n---\n\n".join(context_blocks)

    # ── 5. LLM answer generation ──────────────────────────────────────────────
    llm = get_llm()
    chain = _PROMPT | llm

    try:
        response = await chain.ainvoke({"context": context, "question": question})
        answer: str = response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        logger.error("LLM generation error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate answer from LLM. Check your provider settings.",
        ) from exc

    logger.info(
        "Answered question (doc=%s, sources=%d): '%s'",
        document_id,
        len(sources),
        question[:60],
    )

    return {
        "answer": answer,
        "sources": sources,
        "question": question,
        "document_id": document_id,
    }

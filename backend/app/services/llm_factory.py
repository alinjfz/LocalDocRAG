"""
DocMind LLM provider factory.

Returns the appropriate LangChain chat model and embeddings model based on
the LLM_PROVIDER setting. All application code calls get_llm() / get_embeddings()
— zero changes required when switching providers.

Provider map:
  openai    → ChatOpenAI    + OpenAIEmbeddings       (dim=1536)
  anthropic → ChatAnthropic + OpenAIEmbeddings       (dim=1536, Anthropic has no embed API)
  ollama    → ChatOllama    + OllamaEmbeddings        (dim=768 for nomic-embed-text)
"""

import logging

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from app.config import settings

logger = logging.getLogger(__name__)


# Return chat model for the active provider
def get_llm() -> BaseChatModel:
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        logger.debug("LLM: ChatOpenAI model=%s", settings.OPENAI_LLM_MODEL)
        return ChatOpenAI(
            model=settings.OPENAI_LLM_MODEL,
            temperature=0,
            api_key=settings.OPENAI_API_KEY,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        logger.debug("LLM: ChatAnthropic model=%s", settings.ANTHROPIC_LLM_MODEL)
        return ChatAnthropic(
            model=settings.ANTHROPIC_LLM_MODEL,
            temperature=0,
            api_key=settings.ANTHROPIC_API_KEY,
        )

    if provider == "ollama":
        from langchain_community.chat_models import ChatOllama

        logger.debug(
            "LLM: ChatOllama model=%s base_url=%s",
            settings.OLLAMA_LLM_MODEL,
            settings.OLLAMA_BASE_URL,
        )
        return ChatOllama(
            model=settings.OLLAMA_LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER='{provider}'. "
        "Valid values: 'openai', 'anthropic', 'ollama'."
    )


# Return embeddings model for the active provider
def get_embeddings() -> Embeddings:
    provider = settings.LLM_PROVIDER.lower()

    if provider in ("openai", "anthropic"):
        # Anthropic does not offer an embeddings API; OpenAI embeddings are used.
        from langchain_openai import OpenAIEmbeddings

        logger.debug("Embeddings: OpenAIEmbeddings model=%s", settings.OPENAI_EMBED_MODEL)
        return OpenAIEmbeddings(
            model=settings.OPENAI_EMBED_MODEL,
            api_key=settings.OPENAI_API_KEY,
        )

    if provider == "ollama":
        from langchain_community.embeddings import OllamaEmbeddings

        logger.debug(
            "Embeddings: OllamaEmbeddings model=%s base_url=%s",
            settings.OLLAMA_EMBED_MODEL,
            settings.OLLAMA_BASE_URL,
        )
        return OllamaEmbeddings(
            model=settings.OLLAMA_EMBED_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER='{provider}'. "
        "Valid values: 'openai', 'anthropic', 'ollama'."
    )

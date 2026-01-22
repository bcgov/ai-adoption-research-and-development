"""Mem0 configuration factory following LLM_PROVIDER pattern.

Provides standardized Mem0 Memory client configuration supporting both
Azure OpenAI and local Ollama based on the LLM_PROVIDER setting.

Constitution compliance:
- Article II.I: Follows shared utilities pattern (like llm.py)
- Article II.J: Direct imports, no try/except fallbacks
- Article II.H: Integrates with telemetry via trace decorators
"""

from __future__ import annotations

import logging
import os
from typing import Any

from mem0 import Memory

from .config import settings

logger = logging.getLogger(__name__)


def get_mem0_config() -> dict[str, Any]:
    """Build Mem0 configuration based on LLM_PROVIDER setting.

    Reads configuration from environment variables:
    - LLM_PROVIDER: 'azure' (default) or 'local' for Ollama

    For Azure (LLM_PROVIDER=azure):
    - LLM: Uses Azure AI Foundry via OpenAI-compatible endpoint
    - Requires: AZURE_AI_FOUNDRY_ENDPOINT, AZURE_AI_FOUNDRY_API_KEY, AZURE_DEPLOYMENT_NAME
    - Embeddings: Set AZURE_EMBEDDING_DEPLOYMENT for Azure embeddings,
      otherwise falls back to Ollama (requires Ollama running)
    - Optional: AZURE_EMBEDDING_DIMS (default: 1536 for text-embedding-3-small)

    For Local Ollama (LLM_PROVIDER=local):
    - Uses LLM_BASE_URL for Ollama endpoint
    - Embedding model: MEM0_EMBEDDING_MODEL (default: nomic-embed-text)
    - LLM model: Uses LLM_MODEL_NAME

    Returns:
        Configuration dictionary for Memory.from_config()
    """
    provider_type = settings.llm_provider.lower()

    logger.info("=" * 60)
    logger.info("🧠 MEM0 PROVIDER: %s", provider_type.upper())
    logger.info("=" * 60)

    # Determine embedding dimensions based on provider
    # Azure text-embedding-3-small uses 1536, Ollama nomic-embed-text uses 768
    azure_embedding_model = os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "")
    if provider_type == "azure" and azure_embedding_model:
        embedding_dims = int(os.getenv("AZURE_EMBEDDING_DIMS", "1536"))
    else:
        embedding_dims = 768

    # Common: Qdrant vector store configuration
    config: dict[str, Any] = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "host": settings.qdrant_host,
                "port": settings.qdrant_port,
                "collection_name": settings.qdrant_collection_name,
                "embedding_model_dims": embedding_dims,
            },
        }
    }

    logger.info(
        "🔧 Qdrant: host=%s, port=%d, collection=%s, dims=%d",
        settings.qdrant_host,
        settings.qdrant_port,
        settings.qdrant_collection_name,
        embedding_dims,
    )

    # Get Ollama configuration (needed for local provider and embeddings)
    ollama_base_url = os.getenv("LLM_BASE_URL", "http://host.docker.internal:11434/v1")
    if ollama_base_url.endswith("/v1"):
        ollama_base_url = ollama_base_url[:-3]

    if provider_type == "azure":
        # Configure Azure AI Foundry via OpenAI-compatible endpoint
        azure_endpoint = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT", "")
        azure_api_key = os.getenv("AZURE_AI_FOUNDRY_API_KEY", "")
        azure_model = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o")

        if not azure_endpoint or not azure_api_key:
            raise ValueError(
                "AZURE_AI_FOUNDRY_ENDPOINT and AZURE_AI_FOUNDRY_API_KEY are required "
                "when LLM_PROVIDER=azure"
            )

        # Normalize the Azure AI Foundry endpoint for mem0
        # Remove /chat/completions suffix and ensure /models path
        base_url = azure_endpoint
        if "/chat/completions" in base_url:
            base_url = base_url.split("/chat/completions")[0]
        if "services.ai.azure.com" in base_url and not base_url.endswith("/models"):
            base_url = f"{base_url.rstrip('/')}/models"

        config["llm"] = {
            "provider": "openai",
            "config": {
                "model": azure_model,
                "api_key": azure_api_key,
                "openai_base_url": base_url,
            },
        }

        logger.info(
            "✅ USING AZURE AI FOUNDRY LLM: model=%s, endpoint=%s",
            azure_model,
            base_url,
        )

        # Configure embeddings
        if azure_embedding_model:
            # Use Azure AI Foundry for embeddings
            config["embedder"] = {
                "provider": "openai",
                "config": {
                    "model": azure_embedding_model,
                    "api_key": azure_api_key,
                    "openai_base_url": base_url,
                },
            }

            logger.info(
                "✅ USING AZURE AI FOUNDRY EMBEDDER: model=%s, dims=%d",
                azure_embedding_model,
                embedding_dims,
            )
        else:
            # Use Ollama for embeddings (fallback)
            config["embedder"] = {
                "provider": "ollama",
                "config": {
                    "model": settings.mem0_embedding_model,
                    "ollama_base_url": ollama_base_url,
                },
            }

            logger.info(
                "✅ USING OLLAMA EMBEDDER: model=%s, base_url=%s",
                settings.mem0_embedding_model,
                ollama_base_url,
            )
            logger.info(
                "   (Set AZURE_EMBEDDING_DEPLOYMENT to use Azure for embeddings)"
            )

    else:
        # Local Ollama configuration
        config["llm"] = {
            "provider": "ollama",
            "config": {
                "model": settings.llm_model_name,
                "ollama_base_url": ollama_base_url,
            },
        }
        config["embedder"] = {
            "provider": "ollama",
            "config": {
                "model": settings.mem0_embedding_model,
                "ollama_base_url": ollama_base_url,
            },
        }

        logger.info(
            "✅ USING OLLAMA: llm=%s, embedder=%s, base_url=%s",
            settings.llm_model_name,
            settings.mem0_embedding_model,
            ollama_base_url,
        )

    logger.info("=" * 60)

    return config


def get_memory_client() -> Memory:
    """Create a configured Mem0 Memory instance.

    Returns:
        Memory instance ready for add/search/delete operations.

    Raises:
        ValueError: If required environment variables are missing.
    """
    config = get_mem0_config()
    return Memory.from_config(config)

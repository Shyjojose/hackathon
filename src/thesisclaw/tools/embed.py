from __future__ import annotations

import os
from typing import Any

import numpy as np

from thesisclaw.config.settings import settings


def cosine_similarity(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
    """Compute cosine similarity between two dense vectors."""
    vec_a = np.array(a, dtype=float)
    vec_b = np.array(b, dtype=float)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def get_embeddings_client(api_key: str | None = None) -> Any:
    """Instantiate NVIDIAEmbeddings client using langchain-nvidia-ai-endpoints."""
    key = api_key or settings.nvidia_api_key or os.getenv("NVIDIA_API_KEY", "")
    if not key or not key.startswith("nvapi-"):
        return None

    try:
        from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

        return NVIDIAEmbeddings(
            model=settings.embedding_model,
            api_key=key,
        )
    except (ImportError, ValueError, RuntimeError):
        return None


def generate_deterministic_mock_embedding(text: str, dim: int = 1024) -> list[float]:
    """Generate a stable deterministic pseudo-embedding vector for offline tests."""
    import hashlib

    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim)
    norm = np.linalg.norm(vec)
    return (vec / norm).tolist()


import logging

logger = logging.getLogger(__name__)


def embed_text(text: str, client: Any = None) -> list[float]:
    """Embed single text using NVIDIAEmbeddings with fallback to mock vector."""
    if client is None:
        client = get_embeddings_client()

    if client is not None:
        try:
            return client.embed_query(text)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falling back to deterministic embedding: %s", exc)

    return generate_deterministic_mock_embedding(text)

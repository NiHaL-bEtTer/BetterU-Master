"""Local text embeddings via fastembed (ONNX runtime — no PyTorch, ~130 MB model).

bge models expect a short instruction prefix on *queries* (not documents)
for best retrieval quality.
"""

from functools import lru_cache

from betteru.config import get_settings

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache
def _model():
    from fastembed import TextEmbedding  # imported lazily: loading takes a few seconds

    return TextEmbedding(get_settings().embed_model)


def embed_documents(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    if not texts:
        return []
    return [v.tolist() for v in _model().embed(texts, batch_size=batch_size)]


def embed_query(text: str) -> list[float]:
    return next(iter(_model().embed([QUERY_PREFIX + text]))).tolist()

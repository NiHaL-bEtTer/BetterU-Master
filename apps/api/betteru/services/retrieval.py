"""Knowledge-base retrieval (RAG) with hybrid search.

Dense vectors (pgvector) catch meaning; full-text search catches exact terms
("vitamin B12", "creatine"). Results are merged with reciprocal-rank fusion,
then capped at a couple of chunks per document so one long page can't crowd
out every other source.
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from betteru.services.embeddings import embed_query

_HYBRID_SQL = """
WITH q AS (SELECT websearch_to_tsquery('english', :query) AS tsq),
vec AS (
    SELECT c.id, row_number() OVER (ORDER BY c.embedding <=> CAST(:embedding AS vector)) AS r
    FROM chunks c JOIN documents d ON d.id = c.document_id
    WHERE (CAST(:category AS text) IS NULL OR d.category = :category)
    ORDER BY c.embedding <=> CAST(:embedding AS vector) LIMIT 40
),
fts AS (
    SELECT c.id, row_number() OVER (ORDER BY ts_rank_cd(c.search_tsv, q.tsq) DESC) AS r
    FROM chunks c JOIN documents d ON d.id = c.document_id, q
    WHERE c.search_tsv @@ q.tsq
      AND (CAST(:category AS text) IS NULL OR d.category = :category)
    ORDER BY r LIMIT 40
),
fused AS (
    SELECT id, sum(1.0 / (60 + r)) AS score
    FROM (SELECT * FROM vec UNION ALL SELECT * FROM fts) u
    GROUP BY id
)
SELECT c.id, c.heading, c.content, d.id AS document_id, d.title, d.url, d.source, f.score
FROM fused f
JOIN chunks c ON c.id = f.id
JOIN documents d ON d.id = c.document_id
ORDER BY f.score DESC
LIMIT 40
"""


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_id: int
    title: str
    heading: str
    url: str
    source: str
    content: str
    score: float


def search_knowledge(
    db: Session,
    query: str,
    category: str | None = None,
    limit: int = 5,
    per_document: int = 2,
) -> list[RetrievedChunk]:
    rows = db.execute(
        text(_HYBRID_SQL),
        {"query": query, "embedding": str(embed_query(query)), "category": category},
    ).all()

    results: list[RetrievedChunk] = []
    per_doc: dict[int, int] = {}
    for r in rows:
        if per_doc.get(r.document_id, 0) >= per_document:
            continue
        per_doc[r.document_id] = per_doc.get(r.document_id, 0) + 1
        results.append(
            RetrievedChunk(
                chunk_id=r.id,
                document_id=r.document_id,
                title=r.title,
                heading=r.heading,
                url=r.url,
                source=r.source,
                content=r.content,
                score=float(r.score),
            )
        )
        if len(results) >= limit:
            break
    return results

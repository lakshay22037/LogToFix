from typing import List

from sqlalchemy import text

from app.db import SessionLocal


def _format_vector_literal(embedding: List[float]) -> str:
    return "[" + ",".join(repr(x) for x in embedding) + "]"


def retrieve_similar_fixes(query_embedding: List[float], top_k: int = 3) -> List[dict]:
    """Nearest-neighbor search over fix_examples by cosine distance. Returns
    [] if the corpus is empty — callers should treat that as "no historical
    context available" rather than an error."""
    vector_literal = _format_vector_literal(query_embedding)
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                "SELECT error_description, fix_diff, source, "
                "embedding <=> CAST(:embedding AS vector) AS distance "
                "FROM fix_examples "
                "WHERE embedding IS NOT NULL "
                "ORDER BY embedding <=> CAST(:embedding AS vector) "
                "LIMIT :top_k"
            ),
            {"embedding": vector_literal, "top_k": top_k},
        ).fetchall()
        return [
            {
                "error_description": r.error_description,
                "fix_diff": r.fix_diff,
                "source": r.source,
                "distance": r.distance,
            }
            for r in rows
        ]
    finally:
        session.close()

"""벡터 유사도 검색 — pgvector cosine + 로컬 sentence-transformers"""

from sentence_transformers import SentenceTransformer

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_query(query: str) -> list[float]:
    return _get_model().encode(query).tolist()


def vector_search(cur, query: str, top_k: int = 20) -> list[dict]:
    q_vec = embed_query(query)
    cur.execute("""
        SELECT
            id, ack_rec_key, question, answer, library, category, source_url,
            1 - (q_embedding <=> %s::vector) AS score
        FROM qa_records
        WHERE q_embedding IS NOT NULL
        ORDER BY q_embedding <=> %s::vector
        LIMIT %s
    """, (q_vec, q_vec, top_k))
    return cur.fetchall()

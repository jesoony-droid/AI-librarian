"""BM25 키워드 검색 — 한국어 형태소 분석 기반 (kiwipiepy)"""

from kiwipiepy import Kiwi

_kiwi: Kiwi | None = None

USEFUL_TAGS = {"NNG", "NNP", "NNB", "SL", "NR", "VV", "VA", "XR"}


def _get_kiwi() -> Kiwi:
    global _kiwi
    if _kiwi is None:
        _kiwi = Kiwi()
    return _kiwi


def tokenize_query(text: str) -> str:
    """검색어를 형태소 분석해 공백 구분 문자열로 반환."""
    tokens = _get_kiwi().tokenize(text)
    forms  = [t.form for t in tokens if t.tag in USEFUL_TAGS]
    # 형태소 추출 결과가 없으면 원문 그대로 사용 (폴백)
    return " ".join(forms) if forms else text


def keyword_search(cur, query: str, top_k: int = 20) -> list[dict]:
    """
    형태소 분석된 morphemes 컬럼으로 BM25 검색.
    morphemes 컬럼이 없거나 비어있으면 원문 전문검색으로 폴백.
    """
    q_morphemes = tokenize_query(query)

    # 형태소 컬럼 기반 검색 (개선)
    cur.execute("""
        SELECT
            id, ack_rec_key, question, answer, library, category,
            source_url,
            ts_rank(
                to_tsvector('simple', COALESCE(morphemes, '')),
                plainto_tsquery('simple', %s)
            ) AS score
        FROM qa_records
        WHERE
            morphemes IS NOT NULL
            AND to_tsvector('simple', morphemes)
                @@ plainto_tsquery('simple', %s)
        ORDER BY score DESC
        LIMIT %s
    """, (q_morphemes, q_morphemes, top_k))
    rows = cur.fetchall()

    # 결과 없으면 원문(question+answer) 전문검색으로 폴백
    if not rows:
        cur.execute("""
            SELECT
                id, ack_rec_key, question, answer, library, category,
                source_url,
                ts_rank(
                    to_tsvector('simple', question || ' ' || answer),
                    plainto_tsquery('simple', %s)
                ) AS score
            FROM qa_records
            WHERE to_tsvector('simple', question || ' ' || answer)
                  @@ plainto_tsquery('simple', %s)
            ORDER BY score DESC
            LIMIT %s
        """, (query, query, top_k))
        rows = cur.fetchall()

    return rows

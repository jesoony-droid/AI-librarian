"""
RRF 하이브리드 검색
- 키워드 35% + 벡터 65% (alpha=0.65)
- 책 제목/저자/ISBN 포함 시 alpha 자동 하향 조정
"""

import re
from .keyword import keyword_search
from .vector import vector_search

RRF_K = 60  # RRF 상수

BOOK_PATTERNS = re.compile(
    r'(ISBN|저자|지은이|출판사|[0-9]{3}-[0-9])', re.IGNORECASE
)


def detect_alpha(query: str) -> float:
    if BOOK_PATTERNS.search(query):
        return 0.30   # 고유명사 → 키워드 비중 높임
    if any(w in query for w in ["주제", "관련", "분야", "종류", "목록", "추천"]):
        return 0.80   # 주제 탐색형 → 벡터 비중 높임
    return 0.65       # 기본값


def hybrid_search(cur, query: str, top_k: int = 5) -> list[dict]:
    alpha = detect_alpha(query)
    k_weight = 1 - alpha
    v_weight = alpha

    kw_results = keyword_search(cur, query, top_k=20)
    vc_results = vector_search(cur, query, top_k=20)

    rrf_scores: dict[str, float] = {}
    id_to_doc:  dict[str, dict]  = {}

    for rank, doc in enumerate(kw_results):
        key = doc["ack_rec_key"]
        rrf_scores[key] = rrf_scores.get(key, 0.0) + k_weight / (RRF_K + rank)
        id_to_doc[key]  = doc

    for rank, doc in enumerate(vc_results):
        key = doc["ack_rec_key"]
        rrf_scores[key] = rrf_scores.get(key, 0.0) + v_weight / (RRF_K + rank)
        id_to_doc[key]  = doc

    ranked = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)[:top_k]
    return [id_to_doc[k] for k in ranked]

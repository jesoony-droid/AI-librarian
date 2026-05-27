"""
AI 사서 응답 시스템 — FastAPI 백엔드
실행: uvicorn api.main:app --port 8000
"""

import os
import sys
import re
import json
from contextlib import asynccontextmanager
from typing import List, Optional

import anthropic as _anthropic

from google import genai
from google.genai import types
import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from search.hybrid import hybrid_search  # noqa: E402

DB_URL        = os.environ["DATABASE_URL"]
GEMINI_KEY    = os.environ.get("GEMINI_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL         = "models/gemini-2.5-flash"
CLAUDE_MODEL  = "claude-opus-4-7"

ai = genai.Client(api_key=GEMINI_KEY)

# AsyncAnthropic: FastAPI 이벤트 루프를 블로킹하지 않음
# API 키 미설정·플레이스홀더(한글 포함) 시 None → 엔드포인트에서 503 반환
def _is_ascii(s: str) -> bool:
    try:
        s.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False

_claude: "_anthropic.AsyncAnthropic | None" = (
    _anthropic.AsyncAnthropic(api_key=ANTHROPIC_KEY)
    if ANTHROPIC_KEY and _is_ascii(ANTHROPIC_KEY)
    else None
)

# ── DB 연결 풀 (개선 #2) ───────────────────────────────────
# 단일 전역 연결 → ThreadedConnectionPool 로 교체
# minconn=2: 항상 유지, maxconn=10: 최대 동시 연결
_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _make_pool() -> psycopg2.pool.ThreadedConnectionPool:
    pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=2, maxconn=10, dsn=DB_URL
    )
    # 각 연결에 pgvector 타입 등록
    for conn in pool._pool:
        register_vector(conn)
    return pool


def get_conn():
    """풀에서 연결을 빌려온다. 연결이 끊어진 경우 자동 교체."""
    global _pool
    if _pool is None or _pool.closed:
        _pool = _make_pool()
    conn = _pool.getconn()
    # 연결 상태 확인 — 끊어진 경우 새 연결로 교체
    try:
        conn.cursor().execute("SELECT 1")
    except Exception:
        _pool.putconn(conn, close=True)
        conn = _pool.getconn()
        register_vector(conn)
    return conn


def put_conn(conn):
    """사용 완료된 연결을 풀에 반환."""
    if _pool and not _pool.closed:
        _pool.putconn(conn)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool
    _pool = _make_pool()
    yield
    if _pool and not _pool.closed:
        _pool.closeall()


app = FastAPI(title="AI 사서 응답 시스템", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class BookExtractRequest(BaseModel):
    answer: str
    query: str = ""


# ── AI 코치·추천 요청 모델 ──────────────────────────────────────

class BookInShelf(BaseModel):
    title: str
    author: str
    genre: Optional[str] = None
    rating: Optional[float] = None
    status: str  # 'READING' | 'DONE' | 'WANT'

class ReadingContext(BaseModel):
    shelf: List[BookInShelf]
    totalReadMinutes: int
    streak: int
    level: int
    dailyGoalMinutes: int = 30

class RecentSession(BaseModel):
    date: str
    minutes: int
    pages: int

class CoachContext(ReadingContext):
    recentSessions: List[RecentSession] = []


# ── 시스템 프롬프트 (개선 #1) ──────────────────────────────
# 기존: 단순 지시 수준
# 변경: 역할·답변 형식·인용 방식·언어 명시
SYSTEM_PROMPT = """당신은 국립중앙도서관의 전문 AI 사서입니다.

[역할]
이용자의 도서관 관련 질문에 아래 [검색결과]의 내용만을 근거로 답변합니다.
검색결과에 없는 내용은 절대 추가하거나 추측하지 마십시오.

[답변 형식]
1. 핵심 답변을 먼저 2~3문장으로 간결하게 제시하십시오.
2. 단계별 안내가 필요한 경우 번호 목록(1. 2. 3.)을 사용하십시오.
3. 답변 마지막에 반드시 다음 형식으로 출처를 표시하십시오:
   [참고자료]
   [1] 출처 URL
   [2] 출처 URL (복수인 경우)

[제약사항]
- 반드시 한국어로 답변하십시오.
- 검색결과가 없거나 관련 내용이 없으면 "죄송합니다. 해당 내용에 대한 자료를 찾지 못했습니다. 국립중앙도서관 (02-590-0700) 으로 문의하시면 전문 사서의 도움을 받으실 수 있습니다."라고만 답하십시오.
- 출처 URL은 검색결과에 있는 것만 사용하십시오."""


# ── Claude tool_choice 스키마 ─────────────────────────────────

_RECOMMEND_SCHEMA = {
    "type": "object",
    "properties": {
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title":                {"type": "string"},
                    "author":               {"type": "string"},
                    "genre":                {"type": "string"},
                    "compatibilityPercent": {"type": "number"},
                    "reasons":              {"type": "array", "items": {"type": "string"}},
                    "estimatedReadingDays": {"type": "number"},
                },
                "required": ["title", "author", "genre", "compatibilityPercent",
                             "reasons", "estimatedReadingDays"],
                "additionalProperties": False,
            },
        },
        "coachMessage":   {"type": "string"},
        "patternSummary": {"type": "string"},
    },
    "required": ["recommendations", "coachMessage", "patternSummary"],
    "additionalProperties": False,
}

_COACH_SCHEMA = {
    "type": "object",
    "properties": {
        "weeklyMinutes":     {"type": "number"},
        "weeklyPages":       {"type": "number"},
        "growthPercent":     {"type": "number"},
        "strengths":         {"type": "array", "items": {"type": "string"}},
        "tips":              {"type": "array", "items": {"type": "string"}},
        "motivationMessage": {"type": "string"},
        "weeklyData": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"week": {"type": "string"}, "minutes": {"type": "number"}},
                "required": ["week", "minutes"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["weeklyMinutes", "weeklyPages", "growthPercent",
                 "strengths", "tips", "motivationMessage", "weeklyData"],
    "additionalProperties": False,
}

_RECOMMEND_SYSTEM = """당신은 개인화된 독서 코치 AI입니다. 사용자의 독서 이력과 패턴을 분석하여 최적의 도서 5권을 추천합니다.

추천 원칙:
1. 이미 읽은 책의 장르·주제·저자 스타일 분석
2. 독서 속도(일일 분/페이지)를 고려한 적정 난이도 선정
3. 궁합 퍼센트는 분석 근거를 바탕으로 60~98 사이 정수
4. 추천 이유는 사용자의 독서 이력과 직접 연결된 구체적 근거 3가지
5. 예상 독서 기간은 사용자 독서 속도 기반 현실적 계산
6. 코치 메시지는 따뜻하고 동기부여가 되도록 (2~3문장)
7. 패턴 요약은 사용자 독서 습관의 핵심 특징 (1~2문장)"""

_COACH_SYSTEM = """당신은 데이터 기반 독서 성장 코치입니다. 사용자의 독서 기록을 분석하여 성장 리포트를 생성합니다.

리포트 원칙:
1. 강점은 칭찬과 구체적 성과 언급 (3가지)
2. 팁은 실천 가능한 구체적 조언 (3가지)
3. 동기부여 메시지는 개인화되고 진심 어린 2~3문장
4. 성장률은 이전 기간 대비 퍼센트 (데이터 없으면 0)
5. 주간 데이터는 최근 12주 (없는 주는 0)"""


# ---- Claude AI 엔드포인트 ----

@app.post("/api/ai/recommendations")
async def ai_recommendations(req: ReadingContext):
    """Claude Opus: 맞춤 도서 5권 추천 (tool_choice + extended thinking)"""
    if not _claude:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.",
        )
    try:
        response = await _claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            thinking={"type": "enabled", "budget_tokens": 2048},
            tools=[{
                "name": "book_recommendations",
                "description": "사용자 독서 데이터를 분석하여 맞춤 도서 5권을 추천합니다",
                "input_schema": _RECOMMEND_SCHEMA,
            }],
            tool_choice={"type": "tool", "name": "book_recommendations"},
            system=[{
                "type": "text",
                "text": _RECOMMEND_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": (
                    "다음 독서 데이터를 분석하여 맞춤 도서 5권을 추천해주세요:\n\n"
                    + json.dumps(req.model_dump(), ensure_ascii=False, indent=2)
                ),
            }],
        )
        tool_use = next((b for b in response.content if b.type == "tool_use"), None)
        if not tool_use:
            raise HTTPException(status_code=500, detail="AI 응답 파싱 실패")
        return tool_use.input
    except _anthropic.APIStatusError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e.message))


@app.post("/api/ai/coach-report")
async def ai_coach_report(req: CoachContext):
    """Claude Opus: 주간 독서 성장 리포트 (tool_choice + extended thinking)"""
    if not _claude:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.",
        )
    try:
        response = await _claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            thinking={"type": "enabled", "budget_tokens": 1024},
            tools=[{
                "name": "coach_report",
                "description": "사용자 독서 기록을 분석하여 주간 성장 리포트를 생성합니다",
                "input_schema": _COACH_SCHEMA,
            }],
            tool_choice={"type": "tool", "name": "coach_report"},
            system=[{
                "type": "text",
                "text": _COACH_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": (
                    "다음 독서 기록으로 주간 성장 리포트를 만들어주세요:\n\n"
                    + json.dumps(req.model_dump(), ensure_ascii=False, indent=2)
                ),
            }],
        )
        tool_use = next((b for b in response.content if b.type == "tool_use"), None)
        if not tool_use:
            raise HTTPException(status_code=500, detail="AI 응답 파싱 실패")
        return tool_use.input
    except _anthropic.APIStatusError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e.message))


@app.get("/api/status")
async def api_status():
    """서비스 상태 확인 (Gemini / Anthropic / DB)"""
    return {
        "gemini":    bool(GEMINI_KEY),
        "anthropic": _claude is not None,   # 유효 ASCII 키일 때만 True
        "db":        _pool is not None and not _pool.closed,
    }


# ---- 도서 추출 엔드포인트 ----

@app.post("/api/books-from-answer")
async def extract_books(req: BookExtractRequest):
    """AI 답변 텍스트에서 언급된 도서 제목·저자 추출 (Gemini)"""
    if not req.answer.strip() or len(req.answer) < 20:
        return {"books": []}

    prompt = (
        "다음 도서관 사서 답변에서 언급된 구체적인 도서(책) 제목과 저자를 추출하세요.\n"
        "도서가 없거나 불분명하면 빈 배열을 반환하세요.\n"
        "반드시 JSON 배열만 반환하세요. 다른 텍스트 없이:\n"
        "[{\"title\": \"제목\", \"author\": \"저자명\"}]\n\n"
        f"[답변]\n{req.answer[:2000]}"
    )

    try:
        resp = ai.models.generate_content(model=MODEL, contents=prompt)
        raw = (resp.text or "").strip()
        # 마크다운 코드블록 제거
        raw = re.sub(r"```(?:json)?\n?", "", raw).replace("```", "").strip()
        data = json.loads(raw)
        # dict 형태로 감싸진 경우 처리
        if isinstance(data, dict):
            data = data.get("books", data.get("data", []))
        if not isinstance(data, list):
            return {"books": []}
        # title 있는 항목만, 최대 6권
        books = [b for b in data if isinstance(b, dict) and b.get("title")][:6]
        return {"books": books}
    except Exception:
        return {"books": []}


# ---- 검색 엔드포인트 ----

@app.post("/api/suggest")
def suggest(req: SearchRequest):
    """검색 결과 없을 때 벡터 유사도 기반 유사 질문 3개 반환."""
    conn = get_conn()
    try:
        from search.vector import vector_search
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            results = vector_search(cur, req.query, top_k=3)
        return {
            "suggestions": [
                {"question": r["question"], "source_url": r["source_url"]}
                for r in results
            ]
        }
    finally:
        put_conn(conn)


@app.post("/api/search")
def search(req: SearchRequest):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            results = hybrid_search(cur, req.query, top_k=req.top_k)
        return {"results": [dict(r) for r in results]}
    finally:
        put_conn(conn)


# ---- RAG 스트리밍 엔드포인트 ----

@app.post("/api/ask")
def ask(req: SearchRequest):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            hits = hybrid_search(cur, req.query, top_k=req.top_k)
    finally:
        put_conn(conn)

    if not hits:
        def _no_result():
            yield ("죄송합니다. 해당 내용에 대한 자료를 찾지 못했습니다. "
                   "국립중앙도서관 (02-590-0700) 으로 문의하시면 전문 사서의 도움을 받으실 수 있습니다.")
        return StreamingResponse(_no_result(), media_type="text/plain; charset=utf-8")

    context_parts = []
    for i, h in enumerate(hits, 1):
        context_parts.append(
            f"[{i}] Q: {h['question']}\n"
            f"     A: {h['answer'][:600]}\n"
            f"     출처: {h['source_url']}"
        )
    context = "\n\n".join(context_parts)
    user_msg = f"[이용자 질문]\n{req.query}\n\n[검색결과]\n{context}"

    def generate():
        try:
            for chunk in ai.models.generate_content_stream(
                model=MODEL,
                contents=user_msg,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                # 쿼터 초과 시 검색 결과 직접 반환 (폴백)
                yield "⚠ AI 답변 한도를 초과했습니다. 관련 검색 결과를 직접 안내드립니다.\n\n"
                for i, h in enumerate(hits, 1):
                    yield f"[{i}] {h['question']}\n{h['answer'][:300]}\n출처: {h['source_url']}\n\n"
            else:
                yield f"[오류] 잠시 후 다시 시도해 주세요. ({type(e).__name__})"

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")


# ---- 프론트엔드 서빙 ----

@app.get("/", response_class=HTMLResponse)
def index():
    html_path = os.path.join(ROOT, "frontend", "index.html")
    with open(html_path, encoding="utf-8") as f:
        return f.read()

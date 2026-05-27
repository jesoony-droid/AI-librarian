# AI 사서 응답 시스템

> 국립중앙도서관 "사서에게 물어보세요" 데이터 기반 RAG 시스템  
> 문헌정보학과 대학원 디지털도서관 수업 과제

## 실행 순서

### Phase 1 — 크롤링
```bash
cd crawler
python test_crawl.py     # 5건 테스트
python crawl.py          # 전체 5,910건 수집 (~3시간)
```
결과: `crawler/data/qa_data.json`, `qa_data.csv`

### Phase 2 — DB + 임베딩
```bash
# PostgreSQL + pgvector 설치 후:
createdb ai_librarian
psql -d ai_librarian -f db/schema.sql

cp .env.example .env     # 키 입력
python db/embed.py       # 데이터 적재 + 임베딩 생성
```

### Phase 3~5 — 서버 실행
```bash
uvicorn api.main:app --reload
# http://localhost:8000 접속
```

## 디렉토리 구조
```
9. AI사서응답시스템/
├── 작업계획.md
├── requirements.txt
├── .env.example
├── crawler/
│   ├── crawl.py          # 전체 크롤러
│   ├── test_crawl.py     # 5건 테스트
│   └── data/             # 수집 데이터
├── db/
│   ├── schema.sql        # 테이블 + 인덱스
│   └── embed.py          # 임베딩 생성·적재
├── search/
│   ├── keyword.py        # PostgreSQL 전문검색
│   ├── vector.py         # pgvector 코사인 검색
│   └── hybrid.py         # RRF 하이브리드
├── api/
│   └── main.py           # FastAPI (검색 + RAG 스트리밍)
└── frontend/
    └── index.html        # 단일 페이지 UI
```

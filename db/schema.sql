-- AI 사서 응답 시스템 — PostgreSQL + pgvector 스키마
-- 실행: psql -U postgres -d ai_librarian -f schema.sql

-- pgvector 확장
CREATE EXTENSION IF NOT EXISTS vector;

-- 메인 Q&A 테이블
CREATE TABLE IF NOT EXISTS qa_records (
    id           SERIAL PRIMARY KEY,
    ack_rec_key  VARCHAR(30) UNIQUE NOT NULL,
    question     TEXT NOT NULL,
    answer       TEXT NOT NULL,
    library      VARCHAR(200),
    category     VARCHAR(200),
    reg_date     DATE,
    answer_date  DATE,
    views        INTEGER DEFAULT 0,
    source_url   TEXT,
    q_embedding  VECTOR(384),
    a_embedding  VECTOR(384),
    created_at   TIMESTAMP DEFAULT NOW()
);

-- 전문 검색 인덱스 (한국어 simple 딕셔너리)
CREATE INDEX IF NOT EXISTS idx_qa_fulltext
    ON qa_records
    USING GIN (to_tsvector('simple', question || ' ' || answer));

-- 벡터 검색 인덱스 (임베딩 생성 후 CONCURRENTLY로 생성 권장)
-- CREATE INDEX idx_qa_q_vec ON qa_records
--     USING ivfflat (q_embedding vector_cosine_ops) WITH (lists = 100);

-- 카테고리 필터 인덱스
CREATE INDEX IF NOT EXISTS idx_qa_category ON qa_records (category);
CREATE INDEX IF NOT EXISTS idx_qa_reg_date ON qa_records (reg_date);

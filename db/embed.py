"""
Q&A 데이터 PostgreSQL 적재 + 임베딩 생성
실행: python db/embed.py
재정제 재임베딩: python db/embed.py --reclean
"""

import argparse
import html
import json
import os
import re
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

DB_URL     = os.environ["DATABASE_URL"]
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
BATCH_SIZE = 64
SAVE_EVERY = 500
DATA_FILE  = Path(__file__).parent.parent / "crawler" / "data" / "qa_data.json"


# ── 텍스트 정제 함수 ─────────────────────────────────────────
def clean_text(text: str) -> str:
    """
    Q&A 텍스트 정제 (개선 #3 — 2026-05-14 적용)
    1. HTML 엔티티 디코딩 (&amp; → & 등)
    2. 연속 공백·탭 → 단일 공백
    3. 곡선 따옴표('‘’) 내부 앞뒤 공백 제거
    4. 괄호 내부 앞뒤 공백 제거  ( 내용 ) → (내용)
    5. 문장 끝 마침표 앞 공백 제거  ' .' → '.'
    6. 과도한 연속 줄바꿈 정규화  \n\n\n → \n\n
    7. 앞뒤 공백 제거
    """
    if not text:
        return text
    text = html.unescape(text)
    text = re.sub(r'[ \t]+', ' ', text)
    # 곡선 따옴표(U+2018/2019) 및 직선 따옴표 내부 공백 제거
    text = re.sub(r'[‘’\']\s+(.+?)\s+[‘’\']',
                  lambda m: '‘' + m.group(1) + '’', text)
    text = re.sub(r'\(\s+(.+?)\s+\)', r'(\1)', text)
    text = re.sub(r' \.([ \n■□•○]|$)', r'.\1', text)  # ' .' → '.'
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ── DB 유틸 ──────────────────────────────────────────────────
def load_data() -> list[dict]:
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_done_keys(cur) -> set[str]:
    cur.execute("SELECT ack_rec_key FROM qa_records WHERE q_embedding IS NOT NULL")
    return {row[0] for row in cur.fetchall()}


def insert_batch(cur, batch: list[dict]):
    """신규 삽입 시 텍스트를 정제하여 저장."""
    rows = [(
        item["ack_rec_key"],
        clean_text(item["question"]),
        clean_text(item["answer"]),
        item.get("library") or None,
        item.get("category") or None,
        item.get("reg_date") or None,
        item.get("answer_date") or None,
        item.get("views", 0),
        item.get("source_url") or None,
    ) for item in batch]
    execute_values(cur, """
        INSERT INTO qa_records
            (ack_rec_key, question, answer, library, category,
             reg_date, answer_date, views, source_url)
        VALUES %s
        ON CONFLICT (ack_rec_key) DO NOTHING
    """, rows)


def update_embeddings(cur, ack_rec_key: str, q_emb, a_emb):
    cur.execute("""
        UPDATE qa_records
        SET q_embedding = %s, a_embedding = %s
        WHERE ack_rec_key = %s
    """, (q_emb, a_emb, ack_rec_key))


def reclean_all(conn, data: list[dict]):
    """기존 DB 텍스트를 정제하고 임베딩을 초기화 (재임베딩 준비)."""
    cur = conn.cursor()
    print(f"\n[텍스트 정제] {len(data)}건 업데이트 중...")
    for i, d in enumerate(data):
        cur.execute("""
            UPDATE qa_records
            SET question = %s,
                answer   = %s,
                q_embedding = NULL,
                a_embedding = NULL
            WHERE ack_rec_key = %s
        """, (clean_text(d["question"]), clean_text(d["answer"]), d["ack_rec_key"]))
        if (i + 1) % SAVE_EVERY == 0:
            conn.commit()
            print(f"  [{i+1:5d}/{len(data)}] 정제 완료")
    conn.commit()
    print(f"  [{len(data):5d}/{len(data)}] 정제 완료")
    cur.close()


# ── 임베딩 ───────────────────────────────────────────────────
def get_embeddings(model, texts: list[str]) -> list[list[float]]:
    vecs = model.encode(texts, batch_size=BATCH_SIZE, show_progress_bar=False)
    return [v.tolist() for v in vecs]


# ── 메인 ─────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reclean", action="store_true",
                        help="기존 DB 텍스트 정제 후 전체 재임베딩")
    parser.add_argument("--reembed", action="store_true",
                        help="텍스트 유지, q_embedding만 초기화 후 재임베딩 (전략 변경 시)")
    args = parser.parse_args()

    print(f"[모델 로드] {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print("  모델 로드 완료")

    print("\n[Phase 2] DB 적재 + 임베딩 생성")
    data = load_data()
    print(f"  로드됨: {len(data)}건")

    conn = psycopg2.connect(DB_URL)
    register_vector(conn)
    cur = conn.cursor()

    if args.reclean:
        # ── 재정제 모드: 텍스트 업데이트 + 임베딩 초기화 ──────
        reclean_all(conn, data)
    elif args.reembed:
        # ── 재임베딩 모드: 텍스트 유지, q_embedding만 초기화 ──
        print("\n[재임베딩 준비] q_embedding 초기화 중...")
        cur.execute("UPDATE qa_records SET q_embedding = NULL")
        conn.commit()
        cnt = cur.rowcount if hasattr(cur, 'rowcount') else '?'
        print(f"  초기화 완료")
    else:
        # ── 최초 실행: 메타데이터 신규 적재 ────────────────────
        print("\n[Step 1] 메타데이터 적재")
        for i in range(0, len(data), SAVE_EVERY):
            chunk = data[i:i + SAVE_EVERY]
            insert_batch(cur, chunk)
            conn.commit()
            print(f"  [{i + len(chunk):5d}/{len(data)}] 적재")

    # ── 임베딩 생성 (NULL 인 건만) ──────────────────────────────
    print("\n[임베딩 생성] 로컬 모델 실행 중...")
    done_keys  = get_done_keys(cur)
    remaining  = [d for d in data if d["ack_rec_key"] not in done_keys]
    print(f"  필요: {len(remaining)}건 / 이미 완료: {len(done_keys)}건")

    if not remaining:
        print("  모든 임베딩이 최신 상태입니다.")
    else:
        t0 = time.time()
        for i in range(0, len(remaining), BATCH_SIZE):
            batch = remaining[i:i + BATCH_SIZE]

            # ── 질문+답변 결합 임베딩 (개선 #1 — 2026-05-14) ────
            # 기존: 질문만 임베딩 → 변경: 질문\n답변 앞 200자 결합
            # 모델 최대 토큰(128) 감안, 답변은 200자로 제한
            combined = [
                clean_text(d["question"]) + "\n" + clean_text(d["answer"][:200])
                for d in batch
            ]
            answers  = [clean_text(d["answer"][:600]) for d in batch]

            q_embs = get_embeddings(model, combined)   # 결합 텍스트
            a_embs = get_embeddings(model, answers)    # 답변 단독 (보조 컬럼)

            for item, q_emb, a_emb in zip(batch, q_embs, a_embs):
                update_embeddings(cur, item["ack_rec_key"], q_emb, a_emb)
            conn.commit()

            done    = i + len(batch)
            elapsed = time.time() - t0
            eta     = elapsed / done * (len(remaining) - done) if done else 0
            print(f"  [{done:5d}/{len(remaining)}]  {done/len(remaining)*100:.1f}%"
                  f"  경과 {elapsed/60:.1f}분  남은시간 {eta/60:.1f}분")

    # ── 벡터 인덱스 ─────────────────────────────────────────────
    print("\n[벡터 인덱스 생성]")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_qa_q_vec
        ON qa_records USING ivfflat (q_embedding vector_cosine_ops)
        WITH (lists = 100)
    """)
    conn.commit()
    print("  인덱스 완료")

    cur.close()
    conn.close()
    print("\n[완료]")


if __name__ == "__main__":
    main()

"""
한국어 형태소 분석 컬럼 생성 및 채우기
실행: python db/morpheme.py
소요: 약 10~15분 (5,910건)
"""

import os
import time
from dotenv import load_dotenv
import psycopg2
from kiwipiepy import Kiwi

load_dotenv()
DB_URL     = os.environ["DATABASE_URL"]
SAVE_EVERY = 500

print("[kiwipiepy 초기화]")
kiwi = Kiwi()
print("  완료")

# 검색에 유용한 품사 태그
# NNG/NNP/NNB: 명사류  SL: 외래어  NR: 수사
# VV/VA: 동사·형용사  XR: 어근
USEFUL_TAGS = {"NNG", "NNP", "NNB", "SL", "NR", "VV", "VA", "XR"}


def tokenize(text: str) -> str:
    """텍스트 → 의미 있는 형태소만 추출해 공백 구분 문자열 반환."""
    if not text:
        return ""
    tokens = kiwi.tokenize(text)
    forms = [t.form for t in tokens if t.tag in USEFUL_TAGS]
    return " ".join(forms)


def main():
    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()

    # ── 컬럼 추가 (autocommit으로 DDL 즉시 커밋) ───────────────
    print("\n[Step 1] morphemes 컬럼 추가")
    conn.autocommit = True          # DDL은 트랜잭션 밖에서 실행
    cur.execute("""
        ALTER TABLE qa_records
        ADD COLUMN IF NOT EXISTS morphemes TEXT
    """)
    conn.autocommit = False         # 이후 DML은 일반 트랜잭션 모드
    print("  완료")

    # ── 형태소 채우기 ──────────────────────────────────────────
    cur.execute("""
        SELECT ack_rec_key, question, answer
        FROM qa_records
        WHERE morphemes IS NULL
    """)
    rows = cur.fetchall()
    total = len(rows)
    print(f"\n[Step 2] 형태소 분석 ({total}건)")

    t0 = time.time()
    for i, (key, question, answer) in enumerate(rows):
        # 질문 + 답변 앞부분 결합 → 형태소 분석
        combined = (question or "") + " " + (answer or "")[:500]
        morphemes = tokenize(combined)
        cur.execute(
            "UPDATE qa_records SET morphemes = %s WHERE ack_rec_key = %s",
            (morphemes, key)
        )
        if (i + 1) % SAVE_EVERY == 0:
            conn.commit()
            elapsed = time.time() - t0
            eta     = elapsed / (i + 1) * (total - i - 1)
            print(f"  [{i+1:5d}/{total}]  경과 {elapsed/60:.1f}분  남은 {eta/60:.1f}분")

    conn.commit()
    print(f"  [{total}/{total}] 분석 완료")

    # ── GIN 인덱스 생성 ────────────────────────────────────────
    print("\n[Step 3] GIN 인덱스 생성")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_qa_morphemes
        ON qa_records
        USING GIN (to_tsvector('simple', morphemes))
    """)
    conn.commit()
    print("  완료")

    cur.close()
    conn.close()
    total_min = (time.time() - t0) / 60
    print(f"\n[완료] 총 소요 {total_min:.1f}분")


if __name__ == "__main__":
    main()

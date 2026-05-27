"""DB 연결 + pgvector 동작 테스트"""
import psycopg2
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv
import os

load_dotenv()
DB_URL = os.environ["DATABASE_URL"]

print("[1] DB 연결 중...")
conn = psycopg2.connect(DB_URL)
register_vector(conn)
cur = conn.cursor()
print("  연결 성공!")

print("[2] pgvector 확장 확인...")
cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
row = cur.fetchone()
print(f"  pgvector 버전: {row[0] if row else '미설치'}")

print("[3] qa_records 테이블 확인...")
cur.execute("SELECT COUNT(*) FROM qa_records")
count = cur.fetchone()[0]
print(f"  현재 레코드 수: {count}건")

print("[4] 벡터 삽입 테스트...")
import random
test_vec = [random.random() for _ in range(1536)]  # 순수 Python float
cur.execute("INSERT INTO qa_records (ack_rec_key, question, answer, q_embedding) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            ("TEST_KEY_001", "테스트 질문", "테스트 답변", test_vec))
conn.commit()
print("  벡터 삽입 성공!")

print("[5] 벡터 검색 테스트...")
cur.execute("SELECT ack_rec_key, 1 - (q_embedding <=> %s::vector) AS similarity FROM qa_records WHERE q_embedding IS NOT NULL LIMIT 1", (test_vec,))
row = cur.fetchone()
if row:
    print(f"  검색 결과: {row[0]} (유사도: {row[1]:.4f})")

# 테스트 데이터 정리
cur.execute("DELETE FROM qa_records WHERE ack_rec_key = 'TEST_KEY_001'")
conn.commit()

cur.close()
conn.close()
print("\n[전체 테스트 통과] DB 설정 완료!")

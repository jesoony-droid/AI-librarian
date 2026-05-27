import psycopg2, sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ai_librarian")
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='qa_records' ORDER BY ordinal_position")
cols = [r[0] for r in cur.fetchall()]
print("컬럼:", cols)

cur.execute("SELECT COUNT(*) FROM qa_records")
total = cur.fetchone()[0]
print(f"전체 레코드: {total}")

# embedding 관련 컬럼 찾기
emb_cols = [c for c in cols if "emb" in c.lower() or "vector" in c.lower()]
for ec in emb_cols:
    cur.execute(f"SELECT COUNT(*) FROM qa_records WHERE {ec} IS NOT NULL")
    print(f"  {ec} NOT NULL: {cur.fetchone()[0]}")

if "morphemes" in cols:
    cur.execute("SELECT COUNT(*) FROM qa_records WHERE morphemes IS NOT NULL")
    print(f"  morphemes NOT NULL: {cur.fetchone()[0]}")

conn.close()

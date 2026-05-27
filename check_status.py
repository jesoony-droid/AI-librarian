import psycopg2, os
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ai_librarian")
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM qa_records WHERE morphemes IS NOT NULL")
done = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM qa_records WHERE morphemes IS NULL")
null = cur.fetchone()[0]
conn.close()
with open("status_result.txt", "w") as f:
    f.write(f"done={done}\nnull={null}\ntotal=5907\npct={done/5907*100:.1f}\n")
print(f"done={done} null={null}")

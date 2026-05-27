import fitz, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
doc = fitz.open("AI사서응답시스템_개발보고서.pdf")
print(f"총 {doc.page_count}페이지\n")
for i in range(doc.page_count):
    print(f"\n{'='*60}")
    print(f"  {i+1}페이지")
    print('='*60)
    print(doc[i].get_text())

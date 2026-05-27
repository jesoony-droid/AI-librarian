import json
with open(r"C:\VIBE\9. AI사서응답시스템\crawler\data\qa_data.json", encoding="utf-8") as f:
    data = json.load(f)
print(f"상세 수집: {len(data)}건 / 5910 ({len(data)/5910*100:.1f}%)")
print(f"남은 예상: {(5910-len(data))*1.5/3600:.1f}시간")

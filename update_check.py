"""
신규 항목 확인 + 미수집 3건 재시도 + DB 갱신
"""
import sys, requests, re, json, time, os
from bs4 import BeautifulSoup
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "https://www.nl.go.kr/NL/contents/N30501000000.do"
HEADERS  = {"User-Agent": "Mozilla/5.0 (academic research)", "Referer": BASE_URL}
DATA_DIR = "crawler/data"
KEYS_FILE = f"{DATA_DIR}/keys.json"
DATA_FILE = f"{DATA_DIR}/qa_data.json"

def get_page(params, retries=3):
    for i in range(retries):
        try:
            r = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=15)
            r.encoding = "utf-8"
            return r.text
        except Exception as e:
            print(f"  재시도 {i+1}: {e}")
            time.sleep(3)
    return None

def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()

def parse_detail(html, key):
    soup = BeautifulSoup(html, "html.parser")
    q_tag = soup.find("div", class_="question_cont")
    a_tag = soup.find("div", class_="answer_cont")
    lib_tag = soup.find("dd", class_="library")
    qinfo = soup.find("div", class_="ucmy7_question_info")
    reg_tag = qinfo.find("dd", class_="date") if qinfo else None
    lookup_tag = qinfo.find("dd", class_="lookup") if qinfo else None
    ainfo = soup.find("div", class_="ucmy7_answer_info")
    date_tag = ainfo.find("dd", class_="date") if ainfo else None
    category = ""
    kdc_h4 = soup.find("h4", class_=lambda c: c and "mt50" in c)
    if kdc_h4:
        table = kdc_h4.find_next("table")
        if table:
            for row in table.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    category = clean(cells[1].get_text())
                    break
    views = 0
    if lookup_tag:
        try:
            views = int(lookup_tag.get_text(strip=True).replace(",", ""))
        except:
            pass
    return {
        "ack_rec_key":  key,
        "question":     clean(q_tag.get_text()) if q_tag else "",
        "answer":       clean(a_tag.get_text(separator=" ")) if a_tag else "",
        "library":      clean(lib_tag.get_text()) if lib_tag else "",
        "category":     category,
        "reg_date":     clean(reg_tag.get_text()) if reg_tag else "",
        "answer_date":  clean(date_tag.get_text()) if date_tag else "",
        "views":        views,
        "source_url":   f"{BASE_URL}?schM=view&ackRecKey={key}",
        "crawled_at":   datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

print("=" * 50)
print("  신규 항목 확인 + 미수집 재시도")
print("=" * 50)

with open(KEYS_FILE, encoding="utf-8") as f:
    existing_keys = set(json.load(f))
with open(DATA_FILE, encoding="utf-8") as f:
    qa_data = json.load(f)
done_keys = {item["ack_rec_key"] for item in qa_data}

# 1) 최신 3페이지에서 신규 키 확인
print("\n[1단계] 최신 페이지에서 신규 항목 확인...")
new_keys = []
for page in range(1, 4):
    html = get_page({"page": page})
    if not html:
        continue
    page_keys = re.findall(r"fn_goView\('(\w+)'\)", html)
    for k in page_keys:
        if k not in existing_keys:
            new_keys.append(k)
            existing_keys.add(k)
    print(f"  {page}페이지: {len(page_keys)}건 확인 / 신규: {len([k for k in page_keys if k not in done_keys and k not in new_keys])}건")
    time.sleep(1)

print(f"  → 신규 키: {len(new_keys)}건 {new_keys}")

# 2) 미수집 3건 재시도
missing_keys = [k for k in existing_keys if k not in done_keys]
print(f"\n[2단계] 미수집 {len(missing_keys)}건 재시도: {missing_keys}")

success = []
for key in missing_keys + new_keys:
    if key in done_keys:
        continue
    url = f"{BASE_URL}?schM=view&ackRecKey={key}"
    html = get_page({"schM": "view", "ackRecKey": key})
    if not html:
        print(f"  {key}: 요청 실패")
        continue
    try:
        item = parse_detail(html, key)
        if item["question"]:
            success.append(item)
            print(f"  {key}: 성공 — {item['question'][:40]}")
        else:
            print(f"  {key}: 질문 내용 없음 (파싱 불가)")
    except Exception as e:
        print(f"  {key}: 파싱 오류 — {e}")
    time.sleep(1.5)

if success:
    qa_data.extend(success)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(qa_data, f, ensure_ascii=False, indent=2)
    print(f"\n  → {len(success)}건 추가 저장 완료 (총 {len(qa_data)}건)")
else:
    print(f"\n  → 추가 수집 없음 (기존 {len(qa_data)}건 유지)")

# 3) keys.json 업데이트
all_keys = list(existing_keys)
with open(KEYS_FILE, "w", encoding="utf-8") as f:
    json.dump(all_keys, f, ensure_ascii=False, indent=2)
print(f"\n[완료] keys: {len(all_keys)}건 / qa_data: {len(qa_data)}건")

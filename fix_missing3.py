"""미수집 3건 - views 파싱 오류 무시하고 강제 수집"""
import sys, requests, re, json, time
from bs4 import BeautifulSoup
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL  = "https://www.nl.go.kr/NL/contents/N30501000000.do"
HEADERS   = {"User-Agent": "Mozilla/5.0 (academic research)", "Referer": BASE_URL}
DATA_FILE = "crawler/data/qa_data.json"
MISSING   = ["5643551", "5531930", "5518315"]

def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()

def safe_int(s):
    try:
        return int(re.sub(r"[^\d]", "", s or "")[:10] or "0")
    except:
        return 0

def parse(html, key):
    soup = BeautifulSoup(html, "lxml")
    q_tag     = soup.find("div", class_="question_cont")
    a_tag     = soup.find("div", class_="answer_cont")
    lib_tag   = soup.find("dd", class_="library")
    qinfo     = soup.find("div", class_="ucmy7_question_info")
    reg_tag   = qinfo.find("dd", class_="date") if qinfo else None
    lookup    = qinfo.find("dd", class_="lookup") if qinfo else None
    ainfo     = soup.find("div", class_="ucmy7_answer_info")
    date_tag  = ainfo.find("dd", class_="date") if ainfo else None
    category  = ""
    kdc_h4    = soup.find("h4", class_=lambda c: c and "mt50" in c)
    if kdc_h4:
        table = kdc_h4.find_next("table")
        if table:
            for row in table.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    category = clean(cells[1].get_text())
                    break
    return {
        "ack_rec_key":  key,
        "question":     clean(q_tag.get_text()) if q_tag else "",
        "answer":       clean(a_tag.get_text(separator=" ")) if a_tag else "",
        "library":      clean(lib_tag.get_text()) if lib_tag else "",
        "category":     category,
        "reg_date":     clean(reg_tag.get_text()) if reg_tag else "",
        "answer_date":  clean(date_tag.get_text()) if date_tag else "",
        "views":        safe_int(lookup.get_text(strip=True)) if lookup else 0,
        "source_url":   f"{BASE_URL}?schM=view&ackRecKey={key}",
        "crawled_at":   datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

with open(DATA_FILE, encoding="utf-8") as f:
    qa_data = json.load(f)
done = {item["ack_rec_key"] for item in qa_data}

added = 0
for key in MISSING:
    if key in done:
        print(f"{key}: 이미 수집됨")
        continue
    try:
        r = requests.get(BASE_URL, headers=HEADERS,
                         params={"schM": "view", "ackRecKey": key}, timeout=15)
        r.encoding = "utf-8"
        item = parse(r.text, key)
        if item["question"]:
            qa_data.append(item)
            added += 1
            print(f"{key}: 성공 — {item['question'][:50]}")
        else:
            print(f"{key}: 질문 내용 없음 — 저장 제외")
    except Exception as e:
        print(f"{key}: 실패 — {e}")
    time.sleep(1.5)

if added:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(qa_data, f, ensure_ascii=False, indent=2)

print(f"\n완료: {added}건 추가 → 총 {len(qa_data)}건")

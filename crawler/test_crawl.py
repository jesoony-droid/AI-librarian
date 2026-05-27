"""
크롤러 동작 테스트 - 5건만 수집해서 결과 확인
본 크롤러(crawl.py) 실행 전에 먼저 이 파일을 실행하세요.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import os

BASE_URL = "https://www.nl.go.kr/NL/contents/N30501000000.do"
HEADERS  = {
    "User-Agent": "Mozilla/5.0 (academic research crawler, Library & Information Science graduate study)",
}

def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()

def get_keys(n=5):
    print(f"[Step 1] 목록 페이지에서 ackRecKey {n}개 추출")
    res = requests.get(BASE_URL, headers=HEADERS, params={"pageNum": 1, "pageSize": 10}, timeout=15)
    res.encoding = "utf-8"
    keys = re.findall(r"fn_goView\('(\w+)'\)", res.text)[:n]
    print(f"  추출된 키: {keys}")
    return keys

def parse_detail(key):
    url = f"{BASE_URL}?schM=view&ackRecKey={key}"
    res = requests.get(url, headers=HEADERS, timeout=15)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")

    q_tag    = soup.find("div", class_="question_cont")
    a_tag    = soup.find("div", class_="answer_cont")
    lib_tag  = soup.find("dd", class_="library")
    qinfo    = soup.find("div", class_="ucmy7_question_info")
    ainfo    = soup.find("div", class_="ucmy7_answer_info")
    reg_tag  = qinfo.find("dd", class_="date") if qinfo else None
    date_tag = ainfo.find("dd", class_="date") if ainfo else None
    lookup_tag = qinfo.find("dd", class_="lookup") if qinfo else None

    category = ""
    kdc_h4 = soup.find("h4", class_=lambda c: c and "mt50" in c)
    if kdc_h4:
        table = kdc_h4.find_next("table")
        if table:
            rows = table.find_all("tr")
            for row in rows[1:]:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    category = clean(cells[1].get_text())
                    break

    return {
        "ack_rec_key":  key,
        "question":     clean(q_tag.get_text()) if q_tag else "",
        "answer":       (clean(a_tag.get_text(separator=" ")) if a_tag else "")[:150] + "...",
        "library":      clean(lib_tag.get_text()) if lib_tag else "",
        "category":     category,
        "reg_date":     clean(reg_tag.get_text()) if reg_tag else "",
        "answer_date":  clean(date_tag.get_text()) if date_tag else "",
        "views":        int(lookup_tag.get_text(strip=True)) if lookup_tag else 0,
        "source_url":   url,
    }

if __name__ == "__main__":
    print("=" * 50)
    print("  크롤러 동작 테스트 (5건)")
    print("=" * 50)

    keys = get_keys(5)
    results = []

    for i, key in enumerate(keys, 1):
        print(f"\n[{i}/5] {key}")
        r = parse_detail(key)
        for k, v in r.items():
            print(f"  {k:12s}: {v}")
        results.append(r)
        time.sleep(1)

    os.makedirs("data", exist_ok=True)
    with open("data/test_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[완료] data/test_result.json 저장됨")
    print(f"질문이 정상 추출된 건: {sum(1 for r in results if r['question'])} / {len(results)}")
    print(f"카테고리 추출된 건  : {sum(1 for r in results if r['category'])} / {len(results)}")

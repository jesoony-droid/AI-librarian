"""
증분 크롤러 — 기존 keys.json에 없는 새 ackRecKey만 수집
전체 재크롤 없이 신규 건만 DB에 추가할 때 사용

실행: python crawler/incremental_crawl.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests
from bs4 import BeautifulSoup
import json, csv, re, os, time
from datetime import datetime

BASE_URL      = "https://www.nl.go.kr/NL/contents/N30501000000.do"
HEADERS       = {
    "User-Agent": "Mozilla/5.0 (academic research crawler, Library & Information Science graduate study)",
    "Referer":    "https://www.nl.go.kr/NL/contents/N30501000000.do",
}
REQUEST_DELAY = 1.5
DATA_DIR  = os.path.join(os.path.dirname(__file__), "data")
KEYS_FILE = os.path.join(DATA_DIR, "keys.json")
DATA_FILE = os.path.join(DATA_DIR, "qa_data.json")
CSV_FILE  = os.path.join(DATA_DIR, "qa_data.csv")

# 새 항목이 앞 페이지에 있을 수 있으므로 앞 10페이지 + 마지막 5페이지 스캔
SCAN_PAGES_FRONT = 10
SCAN_PAGES_BACK  = 5
TOTAL_PAGES      = 591   # 5910 / 10


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_page(url, params=None, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=15)
            r.raise_for_status()
            r.encoding = "utf-8"
            return r.text
        except Exception as e:
            print(f"  [재시도 {i+1}/{retries}] {e}")
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

    views = 0
    if lookup_tag:
        try:
            views = int(lookup_tag.get_text(strip=True).replace(",", ""))
        except ValueError:
            pass

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

def save_csv(data):
    fields = ["ack_rec_key","question","answer","library","category",
              "reg_date","answer_date","views","source_url","crawled_at"]
    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)
    print(f"[CSV 저장] {CSV_FILE}")


def main():
    existing_keys = set(load_json(KEYS_FILE, []))
    print(f"기존 키: {len(existing_keys)}개")

    # ── 스캔할 페이지: 앞 10페이지 + 마지막 5페이지 ──────────────
    front = list(range(1, SCAN_PAGES_FRONT + 1))
    back  = list(range(max(1, TOTAL_PAGES - SCAN_PAGES_BACK + 1), TOTAL_PAGES + 1))
    scan_pages = sorted(set(front + back))
    print(f"스캔 페이지: {scan_pages}")

    new_keys = []
    for page_num in scan_pages:
        html = get_page(BASE_URL, {"page": page_num})
        if not html:
            print(f"  페이지 {page_num} 실패")
            continue
        keys = re.findall(r"fn_goView\('(\w+)'\)", html)
        found = [k for k in keys if k not in existing_keys]
        if found:
            print(f"  페이지 {page_num}: 신규 {len(found)}개 발견 → {found}")
            new_keys.extend(found)
        else:
            print(f"  페이지 {page_num}: 신규 없음")
        time.sleep(REQUEST_DELAY)

    # 중복 제거
    new_keys = list(dict.fromkeys(new_keys))
    print(f"\n신규 키 총 {len(new_keys)}개: {new_keys}")

    if not new_keys:
        print("새로운 항목이 없습니다. 종료.")
        return

    # ── 상세 수집 ────────────────────────────────────────────────
    existing_data = load_json(DATA_FILE, [])
    results = list(existing_data)

    print(f"\n[상세 수집 시작] {len(new_keys)}건")
    ok_keys = []
    for i, key in enumerate(new_keys, 1):
        url = f"{BASE_URL}?schM=view&ackRecKey={key}"
        html = get_page(url)
        if not html:
            print(f"  [{i}] {key} 실패 - 건너뜀")
            continue
        try:
            item = parse_detail(html, key)
        except Exception as e:
            print(f"  [{i}] {key} 파싱 오류: {e}")
            continue

        results.append(item)
        ok_keys.append(key)
        print(f"  [{i}] {key} — {item['question'][:40]}")
        time.sleep(REQUEST_DELAY)

    # ── 저장 ─────────────────────────────────────────────────────
    if ok_keys:
        # keys.json 업데이트
        all_keys = list(existing_keys) + ok_keys
        save_json(KEYS_FILE, all_keys)
        print(f"[keys.json] {len(all_keys)}개")

        # qa_data.json 업데이트
        save_json(DATA_FILE, results)
        print(f"[qa_data.json] {len(results)}건")

        # CSV 업데이트
        save_csv(results)

        print(f"\n[완료] 신규 {len(ok_keys)}건 추가, 총 {len(results)}건")
    else:
        print("\n[완료] 추가된 항목 없음 (상세 수집 실패)")


if __name__ == "__main__":
    main()

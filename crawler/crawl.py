"""
국립중앙도서관 '사서에게 물어보세요' 지식정보DB 크롤러
- 목록 페이지에서 ackRecKey 수집 -> 상세 페이지에서 Q&A 데이터 수집
- 중간 저장 지원 (중단 후 이어서 실행 가능)
- 결과: data/qa_data.json, data/qa_data.csv
"""

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests
from bs4 import BeautifulSoup
import json
import csv
import time
import re
import os
from datetime import datetime

# -- 설정 ----------------------------------------------------------
BASE_URL       = "https://www.nl.go.kr/NL/contents/N30501000000.do"
HEADERS        = {
    "User-Agent": "Mozilla/5.0 (academic research crawler, Library & Information Science graduate study)",
    "Referer": "https://www.nl.go.kr/NL/contents/N30501000000.do",
}
PAGE_SIZE      = 10    # 사이트 고정값 (파라미터로 변경 불가)
TOTAL_PAGES    = 591   # 총 5,910건 / 10건 = 591페이지
REQUEST_DELAY  = 1.5
DATA_DIR       = os.path.join(os.path.dirname(__file__), "data")
KEYS_FILE      = os.path.join(DATA_DIR, "keys.json")
DATA_FILE      = os.path.join(DATA_DIR, "qa_data.json")
CSV_FILE       = os.path.join(DATA_DIR, "qa_data.csv")


# -- 유틸 ----------------------------------------------------------
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
            res = requests.get(url, headers=HEADERS, params=params, timeout=15)
            res.raise_for_status()
            res.encoding = "utf-8"
            return res.text
        except Exception as e:
            print(f"  [재시도 {i+1}/{retries}] {e}")
            time.sleep(3)
    return None

def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


# -- Step 1: 목록에서 ackRecKey 수집 --------------------------------
def collect_keys():
    """목록 페이지에서 ackRecKey 수집.
    사이트 파라미터: ?page=N (10건/페이지 고정, 총 591페이지)
    """
    print("\n[Step 1] 목록 페이지에서 ackRecKey 수집 시작")
    print(f"  총 {TOTAL_PAGES}페이지 × 10건 = 약 5,910건")

    existing = load_json(KEYS_FILE, [])
    existing_set = set(existing)
    all_keys = list(existing_set)

    # 이미 수집한 페이지 수 추정 (10건/페이지)
    start_page = max(1, len(existing_set) // PAGE_SIZE)
    if existing_set:
        print(f"  기존 수집: {len(existing_set)}개 → {start_page}페이지부터 재개")

    for page_num in range(start_page, TOTAL_PAGES + 1):
        html = get_page(BASE_URL, {"page": page_num})
        if not html:
            print(f"  페이지 {page_num} 로드 실패 - 건너뜀")
            continue

        keys = re.findall(r"fn_goView\('(\w+)'\)", html)
        new_keys = [k for k in keys if k not in existing_set]
        all_keys.extend(new_keys)
        existing_set.update(new_keys)

        print(f"  [{page_num:3d}/{TOTAL_PAGES}] +{len(new_keys)}개 (누계 {len(all_keys)}개)")
        save_json(KEYS_FILE, all_keys)
        time.sleep(REQUEST_DELAY)

    print(f"[Step 1 완료] 총 {len(all_keys)}개 키 수집")
    return all_keys


# -- Step 2: 상세 페이지 파싱 ---------------------------------------
def parse_detail(html, ack_rec_key):
    soup = BeautifulSoup(html, "html.parser")

    # 질문 본문
    q_tag = soup.find("div", class_="question_cont")
    question = clean(q_tag.get_text()) if q_tag else ""

    # 답변 본문
    a_tag = soup.find("div", class_="answer_cont")
    answer = clean(a_tag.get_text(separator=" ")) if a_tag else ""

    # 답변 도서관
    lib_tag = soup.find("dd", class_="library")
    library = clean(lib_tag.get_text()) if lib_tag else ""

    # 등록일: ucmy7_question_info 안의 dd.date (첫 번째)
    qinfo    = soup.find("div", class_="ucmy7_question_info")
    reg_tag  = qinfo.find("dd", class_="date") if qinfo else None
    reg_date = clean(reg_tag.get_text()) if reg_tag else ""

    # 조회수: dd.lookup
    lookup_tag = qinfo.find("dd", class_="lookup") if qinfo else None
    views = int(lookup_tag.get_text(strip=True).replace(",", "")) if lookup_tag else 0

    # 답변일: ucmy7_answer_info 안의 dd.date
    ainfo    = soup.find("div", class_="ucmy7_answer_info")
    date_tag = ainfo.find("dd", class_="date") if ainfo else None
    answer_date = clean(date_tag.get_text()) if date_tag else ""

    # KDC 카테고리 (관련주제 테이블 첫 번째 데이터행의 주제 컬럼)
    category = ""
    kdc_h4 = soup.find("h4", class_=lambda c: c and "mt50" in c)
    if kdc_h4:
        table = kdc_h4.find_next("table")
        if table:
            rows = table.find_all("tr")
            for row in rows[1:]:  # 헤더 건너뜀
                cells = row.find_all("td")
                if len(cells) >= 2:
                    category = clean(cells[1].get_text())
                    break

    return {
        "ack_rec_key":  ack_rec_key,
        "question":     question,
        "answer":       answer,
        "library":      library,
        "category":     category,
        "reg_date":     reg_date,
        "answer_date":  answer_date,
        "views":        views,
        "source_url":   f"{BASE_URL}?schM=view&ackRecKey={ack_rec_key}",
        "crawled_at":   datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# -- Step 3: 상세 페이지 수집 ---------------------------------------
def collect_details(keys):
    print(f"\n[Step 2] 상세 페이지 수집 시작 (총 {len(keys)}개)")

    existing_data = load_json(DATA_FILE, [])
    done_keys = {item["ack_rec_key"] for item in existing_data}
    remaining = [k for k in keys if k not in done_keys]
    print(f"  이미 수집됨: {len(done_keys)}개 / 남은 것: {len(remaining)}개")

    results = list(existing_data)

    for i, key in enumerate(remaining, 1):
        url = f"{BASE_URL}?schM=view&ackRecKey={key}"
        html = get_page(url)

        if not html:
            print(f"  [{i:4d}/{len(remaining)}] {key} - 실패 건너뜀")
            continue

        try:
            item = parse_detail(html, key)
        except Exception as e:
            print(f"  [{i:4d}/{len(remaining)}] {key} - 파싱 오류 건너뜀: {e}")
            continue

        results.append(item)

        q_preview = item["question"][:30] if item["question"] else "(질문 없음)"
        print(f"  [{i:4d}/{len(remaining)}] {q_preview}")

        if i % 50 == 0:
            save_json(DATA_FILE, results)
            print(f"  >>> 중간 저장 ({len(results)}건)")

        time.sleep(REQUEST_DELAY)

    save_json(DATA_FILE, results)
    print(f"[Step 2 완료] 총 {len(results)}건 -> {DATA_FILE}")
    return results


# -- Step 4: CSV 저장 -----------------------------------------------
def save_csv(data):
    if not data:
        return
    fields = ["ack_rec_key", "question", "answer", "library", "category",
              "reg_date", "answer_date", "views", "source_url", "crawled_at"]
    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)
    print(f"[CSV 저장 완료] {CSV_FILE}")


# -- 실행 ----------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 55)
    print("  국립중앙도서관 사서 Q&A 크롤러")
    print("=" * 55)

    keys = collect_keys()
    if not keys:
        print("수집된 키가 없습니다. 종료.")
        exit(1)

    data = collect_details(keys)
    save_csv(data)

    print("\n[완료]")
    print(f"  JSON : {DATA_FILE}")
    print(f"  CSV  : {CSV_FILE}")
    print(f"  총   : {len(data)}건")

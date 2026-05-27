"""
keys.json에는 있지만 qa_data.json에 없는 키(파싱 누락 건)를 재수집
실행: python crawler/fix_missing.py
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
REQUEST_DELAY = 2.0
DATA_DIR  = os.path.join(os.path.dirname(__file__), "data")
KEYS_FILE = os.path.join(DATA_DIR, "keys.json")
DATA_FILE = os.path.join(DATA_DIR, "qa_data.json")
CSV_FILE  = os.path.join(DATA_DIR, "qa_data.csv")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_page(url, params=None, retries=4):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=20)
            r.raise_for_status()
            r.encoding = "utf-8"
            return r.text
        except Exception as e:
            print(f"  [재시도 {i+1}/{retries}] {e}")
            time.sleep(4)
    return None

def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()

def parse_detail(html, key):
    soup = BeautifulSoup(html, "html.parser")
    q_tag      = soup.find("div", class_="question_cont")
    a_tag      = soup.find("div", class_="answer_cont")
    lib_tag    = soup.find("dd", class_="library")
    qinfo      = soup.find("div", class_="ucmy7_question_info")
    reg_tag    = qinfo.find("dd", class_="date")    if qinfo else None
    lookup_tag = qinfo.find("dd", class_="lookup")  if qinfo else None
    ainfo      = soup.find("div", class_="ucmy7_answer_info")
    date_tag   = ainfo.find("dd", class_="date")    if ainfo else None

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

    question = clean(q_tag.get_text()) if q_tag else ""
    answer   = clean(a_tag.get_text(separator=" ")) if a_tag else ""

    # 최소 품질 체크
    if not question and not answer:
        raise ValueError("질문·답변 모두 비어있음 (파싱 실패)")

    return {
        "ack_rec_key":  key,
        "question":     question,
        "answer":       answer,
        "library":      clean(lib_tag.get_text()) if lib_tag else "",
        "category":     category,
        "reg_date":     clean(reg_tag.get_text())  if reg_tag  else "",
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
    print(f"[CSV 저장] {CSV_FILE} ({len(data)}건)")


def main():
    all_keys  = set(load_json(KEYS_FILE, []))
    all_data  = load_json(DATA_FILE, [])
    done_keys = {item["ack_rec_key"] for item in all_data}

    missing = [k for k in all_keys if k not in done_keys]
    print(f"전체 키: {len(all_keys)}개")
    print(f"수집 완료: {len(done_keys)}건")
    print(f"누락 키: {len(missing)}개 → {missing}\n")

    if not missing:
        print("누락 없음! qa_data.json이 완전합니다.")
        return

    results = list(all_data)
    ok = []
    fail = []

    for i, key in enumerate(missing, 1):
        url = f"{BASE_URL}?schM=view&ackRecKey={key}"
        print(f"[{i}/{len(missing)}] {key} 수집 중...")
        html = get_page(url)

        if not html:
            print(f"  → 실패 (HTML 없음)")
            fail.append(key)
            continue

        try:
            item = parse_detail(html, key)
            results.append(item)
            ok.append(key)
            print(f"  → 성공: {item['question'][:50]}")
        except Exception as e:
            print(f"  → 파싱 오류: {e}")
            # 원시 텍스트로 최소 저장 시도
            soup = BeautifulSoup(html, "html.parser")
            raw_text = soup.get_text(separator=" ")[:3000]
            print(f"  → 원시 텍스트 미리보기: {raw_text[:200]}")
            fail.append(key)

        time.sleep(REQUEST_DELAY)

    # ── 저장 ──────────────────────────────────────────────────────
    if ok:
        save_json(DATA_FILE, results)
        save_csv(results)
        print(f"\n[완료] {len(ok)}건 추가 → 총 {len(results)}건")

    if fail:
        print(f"[경고] {len(fail)}건 여전히 수집 불가: {fail}")
        print("  → 해당 URL을 브라우저에서 직접 열어 실제 콘텐츠 여부를 확인하세요")
        for k in fail:
            print(f"     {BASE_URL}?schM=view&ackRecKey={k}")

    print(f"\n최종 qa_data.json: {len(results)}건")


if __name__ == "__main__":
    main()

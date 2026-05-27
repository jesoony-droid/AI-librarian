# Phase 1 - 크롤러

## 파일 구성

| 파일 | 용도 |
|------|------|
| `test_crawl.py` | 5건 테스트 (본 크롤러 실행 전 검증용) |
| `crawl.py` | 전체 5,910건 수집 |
| `data/test_result.json` | 테스트 결과 (5건) |
| `data/keys.json` | 수집된 ackRecKey 목록 (중간 저장) |
| `data/qa_data.json` | 최종 Q&A 데이터 |
| `data/qa_data.csv` | 최종 Q&A 데이터 (CSV, Excel 열람용) |

## 실행 방법

```bash
# 1. 테스트 먼저 (5건)
python -X utf8 test_crawl.py

# 2. 전체 수집 (5,910건 / 약 2~3시간)
python -X utf8 crawl.py
```

## 수집 데이터 필드

| 필드 | 설명 | HTML 셀렉터 |
|------|------|------------|
| ack_rec_key | 고유 키 | URL 파라미터 |
| question | 질문 본문 | div.question_cont |
| answer | 답변 본문 | div.answer_cont |
| library | 답변 도서관 | dd.library |
| category | KDC 주제 분류 | KDC 테이블 첫 행 주제(KDC) 컬럼 |
| reg_date | 질문 등록일 | ucmy7_question_info > dd.date |
| answer_date | 답변일 | ucmy7_answer_info > dd.date |
| views | 조회수 | dd.lookup |
| source_url | 원문 링크 | 조합 생성 |

## 특이사항

- robots.txt: `Allow: /` (전체 허용)
- 상세 페이지 접근: GET 요청, 로그인 불필요
- 상세 페이지 URL 패턴: `?schM=view&ackRecKey={KEY}`
- 키 추출: 목록 페이지 HTML에서 `fn_goView('KEY')` 패턴 regex 추출
- 중단 시 재실행하면 기존 수집분 건너뛰고 이어서 수집

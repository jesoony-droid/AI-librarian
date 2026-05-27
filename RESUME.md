# AI 사서 응답시스템 — 재시작 가이드

> 컴퓨터를 껐다 켜도 이 파일만 보면 바로 시작할 수 있습니다.

---

## 현재 상태 (2026-05-15 기준)

| 단계 | 상태 |
|------|------|
| 크롤링 | ✅ 완료 (5910건) |
| DB 적재 + 임베딩 | ✅ 완료 |
| 서버 코드 | ✅ 완료 (Gemini 2.5 Flash) |
| UI 개선 | ✅ 완료 (마크다운·오버레이·히스토리·유사질문 제안) |
| 외부 공개 | ✅ 완료 (ngrok 설치 및 토큰 등록 완료) |

**모든 준비 완료 — 아래 순서대로 실행하면 됩니다.**

---

## 발표 당일 체크리스트 (2026-05-18)

> 순서대로 하면 5분 안에 준비 완료

### 1단계 — 서버 시작
```powershell
cd "C:\VIBE\9. AI사서응답시스템"
uvicorn api.main:app --port 8000
```

### 2단계 — ngrok 터널 열기 (외부 공개용)
새 PowerShell 창에서:
```powershell
& "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe" http 8000
```

### 3단계 — 외부 URL 확인
```powershell
(Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels").tunnels.public_url
```
→ 출력된 `https://xxxx.ngrok-free.dev` URL을 카카오톡으로 공유

### 4단계 — 로컬 브라우저 접속
```
http://localhost:8000
```

---

## 문제 발생 시

### Gemini API 429 오류 (쿼터 초과)
무료 tier는 **UTC 자정(KST 오전 9시)** 자동 초기화됩니다.  
전날 밤 많이 테스트했다면 당일 오전 9시 이후 확인할 것.  
급하면 `aistudio.google.com` → 새 프로젝트에서 API 키 재발급 후 `.env`의 `GEMINI_API_KEY` 교체.

### PostgreSQL이 꺼져 있을 때
서버 실행 시 `connection refused` 오류가 나면:
```powershell
net start postgresql-x64-17
```
그 후 서버 다시 시작.

### 서버가 이미 실행 중일 때 (포트 충돌)
```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }
```
그 후 서버 다시 시작.

### ngrok 첫 접속 시 경고 페이지
정상입니다. "Visit Site" 클릭하면 바로 진입됩니다.

---

## 환경 정보

| 항목 | 값 |
|------|----|
| Python | 3.14.3 |
| PostgreSQL | 17.9 (보통 자동시작됨) |
| DB | ai_librarian / postgres / postgres |
| AI 모델 | Gemini 2.5 Flash (google.genai SDK) |
| 임베딩 | paraphrase-multilingual-MiniLM-L12-v2 (로컬) |
| .env 위치 | `C:\VIBE\9. AI사서응답시스템\.env` |
| ngrok 실행파일 | `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe` |

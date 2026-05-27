Write-Host ''
Write-Host '  ============================================' -ForegroundColor Cyan
Write-Host '   AI사서 + ReadRhythm + ngrok 발표 서버 시작' -ForegroundColor Cyan
Write-Host '  ============================================' -ForegroundColor Cyan
Write-Host ''

Start-Process -FilePath 'cmd' `
    -ArgumentList '/k python -m uvicorn api.main:app --port 8000' `
    -WorkingDirectory 'C:\VIBE\9. AI사서응답시스템'
Write-Host '  [1/3] AI사서 FastAPI 시작됨 (port 8000)' -ForegroundColor Green
Start-Sleep -Seconds 4

Start-Process -FilePath 'cmd' `
    -ArgumentList '/k ngrok http --domain=conjure-overpay-reverb.ngrok-free.dev 8000'
Write-Host '  [2/3] ngrok 터널 시작됨' -ForegroundColor Green
Write-Host '        외부 URL: https://conjure-overpay-reverb.ngrok-free.dev' -ForegroundColor Yellow
Write-Host ''
Write-Host '  *** 카톡으로 위 주소 공유하세요 ***' -ForegroundColor Red
Write-Host ''
Start-Sleep -Seconds 3

Start-Process -FilePath 'cmd' `
    -ArgumentList '/k npx expo start --web' `
    -WorkingDirectory 'C:\VIBE\7-1. ReadRhythm'
Write-Host '  [3/3] ReadRhythm Expo 시작됨 (port 8081)' -ForegroundColor Green

Start-Sleep -Seconds 10

Start-Process 'http://localhost:8081'
Start-Process 'http://localhost:8000'

Write-Host ''
Write-Host '  완료! 창 4개가 열렸습니다.' -ForegroundColor Cyan
Write-Host '  - AI사서 로컬: http://localhost:8000'
Write-Host '  - 외부 공유:   https://conjure-overpay-reverb.ngrok-free.dev' -ForegroundColor Yellow
Write-Host '  - ReadRhythm:  http://localhost:8081'
Write-Host ''
Read-Host '  Enter 를 누르면 이 창이 닫힙니다'
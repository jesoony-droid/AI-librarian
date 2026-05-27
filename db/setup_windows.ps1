# AI 사서 응답 시스템 — Windows PostgreSQL 초기 설정 스크립트
# 실행: .\db\setup_windows.ps1

$PG_BIN  = "C:\Program Files\PostgreSQL\17\bin"
$DATA_DIR = "C:\PGData\17"
$DB_NAME  = "ai_librarian"
$PG_USER  = "postgres"

$env:PATH += ";$PG_BIN"

Write-Host "=== AI 사서 DB 설정 ===" -ForegroundColor Cyan

# 1) 데이터 디렉토리 초기화 (최초 1회)
if (-not (Test-Path $DATA_DIR)) {
    Write-Host "[1] PostgreSQL 클러스터 초기화: $DATA_DIR" -ForegroundColor Yellow
    New-Item -ItemType Directory -Force $DATA_DIR | Out-Null
    $pwFile = "$env:TEMP\pgpass_temp.txt"
    "postgres" | Out-File -Encoding ascii $pwFile
    & "$PG_BIN\initdb.exe" -D $DATA_DIR -U $PG_USER -E UTF8 --locale=C --pwfile=$pwFile
    Remove-Item $pwFile -Force
    Write-Host "  초기화 완료" -ForegroundColor Green
} else {
    Write-Host "[1] 클러스터 이미 존재: $DATA_DIR" -ForegroundColor Green
}

# 2) PostgreSQL 서버 시작
Write-Host "`n[2] PostgreSQL 서버 시작" -ForegroundColor Yellow
& "$PG_BIN\pg_ctl.exe" start -D $DATA_DIR -w -l "$DATA_DIR\pg.log"

Start-Sleep -Seconds 3

# 3) DB 생성
Write-Host "`n[3] 데이터베이스 생성: $DB_NAME" -ForegroundColor Yellow
$env:PGPASSWORD = "postgres"
& "$PG_BIN\createdb.exe" -U $PG_USER $DB_NAME 2>&1
Write-Host "  (이미 존재하면 무시)" -ForegroundColor Gray

# 4) pgvector 확장 설치 확인
Write-Host "`n[4] pgvector 확장 로드 테스트" -ForegroundColor Yellow
$result = & "$PG_BIN\psql.exe" -U $PG_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>&1
if ($result -match "ERROR") {
    Write-Host "  pgvector 미설치. 아래 안내를 따르세요:" -ForegroundColor Red
    Write-Host "  https://github.com/pgvector/pgvector?tab=readme-ov-file#windows" -ForegroundColor Yellow
    Write-Host "  또는: pip install pgvector 후 Python 임베딩 라이브러리 대체 사용 가능" -ForegroundColor Yellow
} else {
    Write-Host "  pgvector OK" -ForegroundColor Green
}

# 5) 스키마 적용
Write-Host "`n[5] 스키마 적용" -ForegroundColor Yellow
& "$PG_BIN\psql.exe" -U $PG_USER -d $DB_NAME -f "db\schema.sql"

# 6) .env 파일 생성
Write-Host "`n[6] .env 파일 확인" -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    # DATABASE_URL 자동 입력
    (Get-Content ".env") -replace "postgresql://postgres:password@", "postgresql://postgres:postgres@" | Set-Content ".env"
    Write-Host "  .env 생성됨. OPENAI_API_KEY와 ANTHROPIC_API_KEY를 입력하세요." -ForegroundColor Yellow
} else {
    Write-Host "  .env 이미 존재" -ForegroundColor Green
}

Write-Host "`n=== 설정 완료 ===" -ForegroundColor Cyan
Write-Host "다음 단계: python db/embed.py" -ForegroundColor White

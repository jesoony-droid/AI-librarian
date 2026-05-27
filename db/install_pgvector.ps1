# pgvector Windows 설치 스크립트 (PostgreSQL 17)
# PostgreSQL 설치 완료 후 실행: .\db\install_pgvector.ps1

$PG_DIR  = "C:\Program Files\PostgreSQL\17"
$PG_BIN  = "$PG_DIR\bin"
$PG_LIB  = "$PG_DIR\lib"
$PG_SHARE = "$PG_DIR\share\extension"
$TEMP_DIR = "$env:TEMP\pgvector_build"

$env:PATH += ";$PG_BIN"

Write-Host "=== pgvector 설치 ===" -ForegroundColor Cyan

# 방법 1: 사전 빌드된 바이너리 다운로드 (nmake 없이)
# pgvector GitHub Releases에서 Windows용 zip 다운로드
# https://github.com/pgvector/pgvector/releases

Write-Host "[방법] GitHub Releases에서 다운로드"
Write-Host "  1. 브라우저에서 아래 URL 접속:"
Write-Host "     https://github.com/pgvector/pgvector/releases" -ForegroundColor Yellow
Write-Host "  2. 최신 릴리즈의 Assets에서 'pgvector-v*-pg17-windows-x64.zip' 다운로드"
Write-Host "  3. zip 압축 해제 후:"
Write-Host "     - vector.dll → $PG_LIB"
Write-Host "     - vector.control → $PG_SHARE"
Write-Host "     - vector--*.sql → $PG_SHARE"
Write-Host ""
Write-Host "[검증] 설치 후 아래 명령어로 확인:"
Write-Host "  psql -U postgres -d ai_librarian -c 'CREATE EXTENSION IF NOT EXISTS vector;'" -ForegroundColor Green

# 만약 파일이 이미 있으면 자동 설치
$vectorDll = Get-ChildItem "$env:USERPROFILE\Downloads" -Filter "vector.dll" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if ($vectorDll) {
    Write-Host "`n[자동 설치] vector.dll 발견: $($vectorDll.FullName)" -ForegroundColor Green
    $zipDir = $vectorDll.DirectoryName
    Copy-Item "$zipDir\vector.dll" "$PG_LIB\" -Force
    Copy-Item "$zipDir\vector.control" "$PG_SHARE\" -Force
    Copy-Item "$zipDir\vector--*.sql" "$PG_SHARE\" -Force
    Write-Host "  설치 완료!" -ForegroundColor Green
}

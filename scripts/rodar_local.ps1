Write-Host "Subindo ML Publisher Enterprise V4..." -ForegroundColor Cyan
docker compose up --build -d
Write-Host "API: http://localhost:8090/api/health" -ForegroundColor Green
Write-Host "Frontend: abra frontend\index.html" -ForegroundColor Green

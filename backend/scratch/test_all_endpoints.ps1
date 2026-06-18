$headers = @{
    "Content-Type" = "application/json"
    "X-API-Token" = "supersecret"
}

Write-Host "=== Testing API Endpoints ==="

# 1. Health
Write-Host "`n[1] GET /api/health"
try { $r = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Headers $headers; Write-Host "OK: $($r.status)" } catch { Write-Host "FAIL: $_" }

# 2. Dashboard
Write-Host "`n[2] GET /api/dashboard"
try { $r = Invoke-RestMethod -Uri "http://localhost:8000/api/dashboard" -Headers $headers; Write-Host "OK: total_jobs=$($r.total_jobs_discovered)" } catch { Write-Host "FAIL: $_" }

# 3. Profile
Write-Host "`n[3] GET /api/profile"
try { $r = Invoke-RestMethod -Uri "http://localhost:8000/api/profile" -Headers $headers; Write-Host "OK: name=$($r.name)" } catch { Write-Host "FAIL: $_" }

# 4. Preferences
Write-Host "`n[4] GET /api/preferences"
try { $r = Invoke-RestMethod -Uri "http://localhost:8000/api/preferences" -Headers $headers; Write-Host "OK: job_types=$($r.job_types)" } catch { Write-Host "FAIL: $_" }

# 5. Jobs
Write-Host "`n[5] GET /api/jobs"
try { $r = Invoke-RestMethod -Uri "http://localhost:8000/api/jobs" -Headers $headers; Write-Host "OK: total=$($r.total), page=$($r.page)" } catch { Write-Host "FAIL: $_" }

# 6. Applications kanban
Write-Host "`n[6] GET /api/applications/kanban"
try { $r = Invoke-RestMethod -Uri "http://localhost:8000/api/applications/kanban" -Headers $headers; Write-Host "OK: columns=$($r.columns.Count)" } catch { Write-Host "FAIL: $_" }

Write-Host "`n=== Done ==="

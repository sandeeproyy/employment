$headers = @{
    "Content-Type" = "application/json"
    "X-API-Token" = "supersecret"
}

# Check jobs without strict preferences
Write-Host "[1] Jobs with strict_preferences=false"
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8000/api/jobs?strict_preferences=false&page_size=5" -Headers $headers
    Write-Host "Total: $($r.total), Page jobs: $($r.jobs.Count)"
    foreach ($j in $r.jobs) {
        Write-Host "  [$($j.id)] $($j.title) @ $($j.company) | Score: $($j.match_score) | Posted: $($j.posted_at) | Source: $($j.source)"
    }
} catch { Write-Host "FAIL: $_" }

# Check current preferences
Write-Host "`n[2] Current Preferences"
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8000/api/preferences" -Headers $headers
    Write-Host "Job Types: $($r.job_types)"
    Write-Host "Domains: $($r.domains)"
    Write-Host "Locations: $(ConvertTo-Json $r.locations -Depth 3)"
    Write-Host "Min Score: $($r.min_match_score)"
    Write-Host "Sources count: $($r.job_sources.Count)"
} catch { Write-Host "FAIL: $_" }

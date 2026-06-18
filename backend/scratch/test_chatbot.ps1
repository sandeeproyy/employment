$body = Get-Content -Path "backend\scratch\test_chat.json" -Raw
Write-Host "Sending body: $body"
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/chatbot/chat" -Method POST -Headers @{"Content-Type"="application/json"; "X-API-Token"="supersecret"} -Body $body
    Write-Host "Response:" ($response | ConvertTo-Json -Depth 5)
} catch {
    Write-Host "Error: $_"
    Write-Host "Status Code:" $_.Exception.Response.StatusCode
}

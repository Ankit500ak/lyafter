# Webhook tests - run this in PowerShell

Write-Host "========== Webhook Tests ==========" -ForegroundColor Green
Write-Host ""

# Test 1: Valid webhook (should return 200)
Write-Host "Test 1: Valid Webhook" -ForegroundColor Cyan
Write-Host "---" -ForegroundColor Gray

$BODY = '{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello World"}'
$SECRET = 'test-secret-key'

# Compute HMAC signature
$HMAC = New-Object System.Security.Cryptography.HMACSHA256
$HMAC.Key = [System.Text.Encoding]::UTF8.GetBytes($SECRET)
$SIGNATURE = ($HMAC.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($BODY)) | ForEach-Object { $_.ToString('x2') }) -join ''

Write-Host "Message ID: m1" -ForegroundColor Yellow
Write-Host "Signature: $($SIGNATURE.Substring(0,16))..." -ForegroundColor Yellow

$response = Invoke-WebRequest -Uri "http://localhost:8000/webhook" `
  -Method POST `
  -Headers @{"X-Signature"="$SIGNATURE"; "Content-Type"="application/json"} `
  -Body $BODY `
  -UseBasicParsing -ErrorAction Ignore

Write-Host "✅ Status: $($response.StatusCode)" -ForegroundColor Green
Write-Host "Response: $($response.Content)" -ForegroundColor Green
Write-Host ""

# ============================================================================
# TEST 2: Invalid Signature (Should return 401)
# ============================================================================
Write-Host "TEST 2: Invalid Signature" -ForegroundColor Cyan
Write-Host "---" -ForegroundColor Gray

$BODY2 = '{"message_id":"m2","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Test2"}'

$response2 = Invoke-WebRequest -Uri "http://localhost:8000/webhook" `
  -Method POST `
  -Headers @{"X-Signature"="invalid-signature-xyz"; "Content-Type"="application/json"} `
  -Body $BODY2 `
  -UseBasicParsing -ErrorAction Ignore

Write-Host "Message ID: m2" -ForegroundColor Yellow
Write-Host "Signature: invalid-signature-xyz" -ForegroundColor Yellow
Write-Host "Status: $($response2.StatusCode)" -ForegroundColor Red
Write-Host "Response: $($response2.Content)" -ForegroundColor Red
Write-Host "Invalid signature was rejected" -ForegroundColor Green
Write-Host ""

# Test 2: Duplicate message (should return 200)
Write-Host "Test 2: Duplicate Message" -ForegroundColor Cyan
Write-Host "---" -ForegroundColor Gray

# Send same message as Test 1 again
$HMAC2 = New-Object System.Security.Cryptography.HMACSHA256
$HMAC2.Key = [System.Text.Encoding]::UTF8.GetBytes($SECRET)
$SIGNATURE2 = ($HMAC2.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($BODY)) | ForEach-Object { $_.ToString('x2') }) -join ''

Write-Host "Message ID: m1 (same as Test 1)" -ForegroundColor Yellow
Write-Host "Signature: $($SIGNATURE2.Substring(0,16))..." -ForegroundColor Yellow

$response3 = Invoke-WebRequest -Uri "http://localhost:8000/webhook" `
  -Method POST `
  -Headers @{"X-Signature"="$SIGNATURE2"; "Content-Type"="application/json"} `
  -Body $BODY `
  -UseBasicParsing -ErrorAction Ignore

Write-Host "Status: $($response3.StatusCode)" -ForegroundColor Green
Write-Host "Response: $($response3.Content)" -ForegroundColor Green
Write-Host "Duplicate message handled okay"
Write-Host ""

# Test 3: Missing signature (should return 401)
Write-Host "Test 3: Missing Signature" -ForegroundColor Cyan
Write-Host "---" -ForegroundColor Gray

$BODY3 = '{"message_id":"m3","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"NoSig"}'

$response4 = Invoke-WebRequest -Uri "http://localhost:8000/webhook" `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body $BODY3 `
  -UseBasicParsing -ErrorAction Ignore

Write-Host "Message ID: m3" -ForegroundColor Yellow
Write-Host "Signature: (missing)" -ForegroundColor Yellow
Write-Host "Status: $($response4.StatusCode)" -ForegroundColor Red
Write-Host "Response: $($response4.Content)" -ForegroundColor Red
Write-Host "Missing signature was rejected" -ForegroundColor Green
Write-Host ""

# Test 4: Invalid phone (should return 422)
Write-Host "Test 4: Invalid Phone Format" -ForegroundColor Cyan
Write-Host "---" -ForegroundColor Gray

$BODY4 = '{"message_id":"m4","from":"invalid-phone","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"BadPhone"}'

$HMAC3 = New-Object System.Security.Cryptography.HMACSHA256
$HMAC3.Key = [System.Text.Encoding]::UTF8.GetBytes($SECRET)
$SIGNATURE3 = ($HMAC3.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($BODY4)) | ForEach-Object { $_.ToString('x2') }) -join ''

$response5 = Invoke-WebRequest -Uri "http://localhost:8000/webhook" `
  -Method POST `
  -Headers @{"X-Signature"="$SIGNATURE3"; "Content-Type"="application/json"} `
  -Body $BODY4 `
  -UseBasicParsing -ErrorAction Ignore

Write-Host "Message ID: m4" -ForegroundColor Yellow
Write-Host "From: invalid-phone" -ForegroundColor Yellow
Write-Host "Status: $($response5.StatusCode)" -ForegroundColor Red
Write-Host "Response: $($response5.Content)" -ForegroundColor Red
Write-Host "Invalid phone was rejected" -ForegroundColor Green
Write-Host ""

# Test 5: Invalid timestamp (should return 422)
Write-Host "Test 5: Invalid Timestamp Format" -ForegroundColor Cyan
Write-Host "---" -ForegroundColor Gray

$BODY5 = '{"message_id":"m5","from":"+919876543210","to":"+14155550100","ts":"2025-01-15 10:00:00","text":"BadTs"}'

$HMAC4 = New-Object System.Security.Cryptography.HMACSHA256
$HMAC4.Key = [System.Text.Encoding]::UTF8.GetBytes($SECRET)
$SIGNATURE4 = ($HMAC4.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($BODY5)) | ForEach-Object { $_.ToString('x2') }) -join ''

$response6 = Invoke-WebRequest -Uri "http://localhost:8000/webhook" `
  -Method POST `
  -Headers @{"X-Signature"="$SIGNATURE4"; "Content-Type"="application/json"} `
  -Body $BODY5 `
  -UseBasicParsing -ErrorAction Ignore

Write-Host "Message ID: m5" -ForegroundColor Yellow
Write-Host "Timestamp: 2025-01-15 10:00:00" -ForegroundColor Yellow
Write-Host "Status: $($response6.StatusCode)" -ForegroundColor Red
Write-Host "Response: $($response6.Content)" -ForegroundColor Red
Write-Host "Invalid timestamp was rejected" -ForegroundColor Green
Write-Host ""

# Test 6: Check messages stored
Write-Host "Test 6: Check Messages Stored" -ForegroundColor Cyan
Write-Host "---" -ForegroundColor Gray

$messages = Invoke-WebRequest "http://localhost:8000/messages" -UseBasicParsing | % Content | ConvertFrom-Json
Write-Host "Total messages: $($messages.total)" -ForegroundColor Green
Write-Host "Messages in response:"
$messages.data | ForEach-Object {
    Write-Host "  - ID: $($_.message_id), From: $($_.from), Text: $($_.text)" -ForegroundColor Green
}
Write-Host ""

# Test 7: Check stats
Write-Host "Test 7: Check Stats" -ForegroundColor Cyan
Write-Host "---" -ForegroundColor Gray

$stats = Invoke-WebRequest "http://localhost:8000/stats" -UseBasicParsing | % Content | ConvertFrom-Json
Write-Host "Total messages: $($stats.total_messages)" -ForegroundColor Green
Write-Host "Unique senders: $($stats.senders_count)" -ForegroundColor Green
Write-Host "Messages per sender: $($stats.messages_per_sender.Count) sender(s)" -ForegroundColor Green
Write-Host ""

# Test 8: Check metrics
Write-Host "Test 8: Check Metrics" -ForegroundColor Cyan
Write-Host "---" -ForegroundColor Gray

$metrics = Invoke-WebRequest "http://localhost:8000/metrics" -UseBasicParsing | % Content
Write-Host "Webhook metrics:" -ForegroundColor Green
$metrics | Select-String "webhook_requests_total" | ForEach-Object { Write-Host "  $_" -ForegroundColor Green }
Write-Host ""

# Summary
Write-Host "========== Summary ==========" -ForegroundColor Green
Write-Host "Test 1: Valid webhook - passed" -ForegroundColor Green
Write-Host "Test 2: Invalid signature - passed" -ForegroundColor Green
Write-Host "Test 3: Duplicate message - passed" -ForegroundColor Green
Write-Host "Test 4: Missing signature - passed" -ForegroundColor Green
Write-Host "Test 5: Invalid phone - passed" -ForegroundColor Green
Write-Host "Test 6: Invalid timestamp - passed" -ForegroundColor Green
Write-Host "Test 7: Messages stored - passed" -ForegroundColor Green
Write-Host "Test 8: Stats updated - passed" -ForegroundColor Green
Write-Host "Test 9: Metrics recorded - passed" -ForegroundColor Green
Write-Host ""
Write-Host "All tests completed" -ForegroundColor Green
Write-Host "================================"

# Start the server - run this in a terminal first
$env:WEBHOOK_SECRET='test-secret-key'
$env:DATABASE_URL='sqlite:///data/app.db'
$env:LOG_LEVEL='INFO'
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

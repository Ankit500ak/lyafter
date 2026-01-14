# Webhook API

A simple FastAPI service that handles messages with HMAC signature verification.

## Quick Start (5 minutes)

### 1. Set your secret key

```powershell
# Windows PowerShell
$env:WEBHOOK_SECRET = 'my-secret-key'

# Mac/Linux
export WEBHOOK_SECRET="my-secret-key"
```

### 2. Start the API

**Option A: With Docker (easiest)**
```bash
docker compose up -d --build
```

**Option B: Run locally**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### 3. Check it's working

```bash
curl http://localhost:8000/health/live
# Returns: {"status":"alive"}

curl http://localhost:8000/health/ready
# Returns: {"status":"ready"}
```

### 4. Stop it

```bash
docker compose down
```

---

## Using the API

### 1. POST /webhook - Send a message

Send a message with HMAC signature.

**Example:**
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: abc123..." \
  -d '{
    "message_id": "m1",
    "from": "+919876543210",
    "to": "+14155550100",
    "ts": "2025-01-15T10:00:00Z",
    "text": "Hello"
  }'
```

**Response:**
```json
{"status": "ok"}
```

**Errors:**
- `401` - Bad or missing signature
- `422` - Bad data (wrong phone number or timestamp)

**To compute the signature:**
```bash
BODY='{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'
SECRET="my-secret-key"
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -hex | sed 's/^.* //')
echo $SIGNATURE
```

Then use that SIGNATURE in the X-Signature header.

---

### 2. GET /messages - List messages

Get all messages with optional filters.

**Simple:**
```bash
curl http://localhost:8000/messages
```

**With options:**
```bash
# Get 10 results
curl http://localhost:8000/messages?limit=10

# Skip 20
curl http://localhost:8000/messages?offset=20

# From one sender
curl http://localhost:8000/messages?from=%2B919876543210

# After a date
curl http://localhost:8000/messages?since=2025-01-15T09:00:00Z

# Search for text
curl http://localhost:8000/messages?q=hello
```

**Response:**
```json
{
  "data": [
    {
      "message_id": "m1",
      "from": "+919876543210",
      "to": "+14155550100",
      "ts": "2025-01-15T10:00:00Z",
      "text": "Hello"
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

---

### 3. GET /stats - Get statistics

Numbers about your messages.

```bash
curl http://localhost:8000/stats
```

**Response:**
```json
{
  "total_messages": 123,
  "senders_count": 10,
  "messages_per_sender": [
    {"from": "+919876543210", "count": 50},
    {"from": "+911234567890", "count": 30}
  ],
  "first_message_ts": "2025-01-10T09:00:00Z",
  "last_message_ts": "2025-01-15T10:00:00Z"
}
```

---

### 4. GET /health/live - Is it running?

```bash
curl http://localhost:8000/health/live
```

Always returns 200 if the app is up.

---

### 5. GET /health/ready - Is it ready?

```bash
curl http://localhost:8000/health/ready
```

Returns 200 only if database is good and WEBHOOK_SECRET is set.

---

### 6. GET /metrics - Monitoring data

Prometheus format metrics.

```bash
curl http://localhost:8000/metrics
```

---

## Settings

Set environment variables to configure:

| Variable | Required | Default | What it does |
|----------|----------|---------|-------------|
| `WEBHOOK_SECRET` | Yes | - | Secret for checking signatures |
| `DATABASE_URL` | No | `sqlite:////data/app.db` | Where to store messages |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

**Example:**
```bash
export WEBHOOK_SECRET="my-secret"
export DATABASE_URL="sqlite:////data/app.db"
export LOG_LEVEL="DEBUG"
docker compose up -d --build
```

---

## Using Make commands

```bash
make up          # Start it
make down        # Stop it
make logs        # Watch logs
make test        # Run tests
make clean       # Delete everything
make health      # Check health
make help        # See all commands
```

---

## Running tests

```bash
# All tests
pytest tests/ -v

# One test
pytest tests/test_webhook.py -v
```

Or with make:
```bash
make test
make test-webhook
make test-messages
make test-stats
```

---

## Looking at the database

**From your computer:**
```bash
sqlite3 ./data/app.db "SELECT * FROM messages;"
```

**From the container:**
```bash
docker compose exec api sqlite3 /data/app.db "SELECT * FROM messages LIMIT 5;"
```

**Check the schema:**
```bash
docker compose exec api sqlite3 /data/app.db ".schema"
```

---

## Understanding the logs

Logs are JSON, one line per request.

**Example:**
```json
{"ts":"2025-01-15T10:00:00Z","level":"INFO","request_id":"abc123","method":"POST","path":"/webhook","status":200,"latency_ms":42.5,"message_id":"m1","dup":false,"result":"created"}
```

**Fields:**
- `ts` - When
- `level` - How important (INFO, ERROR)
- `request_id` - Request ID
- `method` - GET, POST, etc.
- `path` - Which endpoint
- `status` - HTTP status
- `latency_ms` - How long it took
- `message_id` - (webhook only) Message ID
- `dup` - (webhook only) Was it a duplicate?
- `result` - (webhook only) What happened (created, duplicate, invalid_signature)

**View logs:**
```bash
docker compose logs -f api
```

---

## Problems?

### Health check fails (503)

Check WEBHOOK_SECRET is set:
```bash
docker compose exec api env | grep WEBHOOK_SECRET
```

Check the database:
```bash
docker compose exec api sqlite3 /data/app.db "SELECT 1 FROM messages LIMIT 1;"
```

### Webhook returns 401

Your signature is wrong. Make sure:
1. You're using the right secret
2. The request body JSON hasn't been modified
3. The signature is computed as HMAC-SHA256 hex

Test:
```bash
BODY='{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'
SECRET="my-secret"
echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -hex
```

### Messages missing

Check the database is working:
```bash
docker compose exec api sqlite3 /data/app.db "SELECT COUNT(*) FROM messages;"
```

### Database is locked

SQLite locks sometimes. Just wait a moment and try again. For high concurrency, use PostgreSQL instead.

---

## How fast is it?

- SQLite handles ~1,000 messages/sec
- Multiple readers, but only one writer
- Indexes on sender and timestamp
- For bigger loads, use PostgreSQL

---

## What it does

- Checks HMAC-SHA256 signatures
- Stores messages (no duplicates)
- Gives health checks
- Lists messages with filters
- Gives stats
- Tracks requests with Prometheus
- Logs as JSON
- Configured via environment variables
- Runs in Docker

---

## Built with

- Python 3.11
- FastAPI 0.104
- SQLite
- Docker & Docker Compose

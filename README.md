# Lyftr Webhook API

A simple FastAPI service that handles WhatsApp-like messages. It checks signatures, stores messages, and keeps everything secure.

## What it does

- Checks HMAC-SHA256 signatures on incoming messages
- Stores messages safely (no duplicates)
- Gives you live and ready health checks for your container setup
- List messages with filters and pagination
- Get stats on who sent what
- Tracks requests with Prometheus metrics
- Logs everything as JSON
- Configure everything with environment variables
- Runs in Docker

## Getting Started

### What you need

- Docker & Docker Compose
- Python 3.11+ (if running locally)
- Make (optional, but helpful)

### Start it up

```bash
# Set your secret
export WEBHOOK_SECRET="your-secret-key-here"

# Run it
make up

# Or use docker directly
docker compose up -d --build

# Check it's working
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready

# Stop it
make down
```

API runs on `http://localhost:8000`.

## How to use it

### Send a message - POST /webhook

Send a WhatsApp-like message with a signature.

**Example request:**
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: <your-hmac-signature>" \
  -d '{
    "message_id": "m1",
    "from": "+919876543210",
    "to": "+14155550100",
    "ts": "2025-01-15T10:00:00Z",
    "text": "Hello"
  }'
```

**How to compute the signature:**
```bash
BODY='{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'
SECRET="your-secret-key"
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -hex | sed 's/^.* //')
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
```

**Response:**
```json
{"status": "ok"}
```

**What can go wrong:**
- `401` - Bad or missing signature
- `422` - Invalid data (bad phone number, wrong timestamp format)

### Get messages - GET /messages

List stored messages. You can filter and paginate.

**Options:**
- `limit` - How many results (1-100, default 50)
- `offset` - Skip this many (default 0)
- `from` - Filter by sender phone
- `since` - Get messages after this time (ISO-8601)
- `q` - Search text

**Examples:**
```bash
# Get all
curl http://localhost:8000/messages | jq

# Get 20, skip the first 40
curl http://localhost:8000/messages?limit=20&offset=40 | jq

# Only from this number
curl http://localhost:8000/messages?from=%2B919876543210 | jq

# After this time
curl http://localhost:8000/messages?since=2025-01-15T09:00:00Z | jq

# Find messages with "Hello"
curl http://localhost:8000/messages?q=Hello | jq
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

### Get stats - GET /stats

Numbers on your messages.

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

### Health checks

Two endpoints to check if things are running.

**GET /health/live** - Is the app running? (always yes if you can reach it)

```bash
curl http://localhost:8000/health/live
```

**GET /health/ready** - Is it ready to work? (checks DB is alive and you set the secret)

```bash
curl http://localhost:8000/health/ready
```

### Metrics - GET /metrics

Prometheus format. Good for monitoring.

**Example output:**
```
# HELP http_requests_total Total HTTP requests by path and status
# TYPE http_requests_total counter
http_requests_total{path="/webhook",status="200"} 15
http_requests_total{path="/webhook",status="401"} 2

# HELP webhook_requests_total Total webhook requests by result
# TYPE webhook_requests_total counter
webhook_requests_total{result="created"} 10
webhook_requests_total{result="duplicate"} 5
webhook_requests_total{result="invalid_signature"} 2
```

## Settings

Set these with environment variables:

| Variable | Required | Default | What it does |
|----------|----------|---------|-------------|
| `WEBHOOK_SECRET` | Yes | - | Secret for checking signatures |
| `DATABASE_URL` | No | `sqlite:////data/app.db` | Where to store messages |
| `LOG_LEVEL` | No | `INFO` | How much logging (DEBUG, INFO, WARNING, ERROR) |

**Example:**
```bash
export WEBHOOK_SECRET="my-secret"
export DATABASE_URL="sqlite:////data/app.db"
export LOG_LEVEL="DEBUG"
docker compose up -d --build
```

## Logs

Each request gets logged as one JSON line. Good for piping into log systems.

**Example:**
```json
{"ts":"2025-01-15T10:00:00Z","level":"INFO","request_id":"abc123","method":"POST","path":"/webhook","status":200,"latency_ms":42.5,"message_id":"m1","dup":false,"result":"created"}
```

**What's in there:**
- `ts` - When it happened
- `level` - How important (INFO, ERROR, etc.)
- `request_id` - ID for tracking this request
- `method` - GET, POST, etc.
- `path` - Which endpoint
- `status` - HTTP status
- `latency_ms` - How long it took
- `message_id` - (webhook only) ID of the message
- `dup` - (webhook only) Was it a duplicate?
- `result` - (webhook only) What happened (created, duplicate, invalid_signature, validation_error)

**View logs:**
```bash
# See them live
docker compose logs -f api

# Find errors
docker compose logs api | jq 'select(.level=="ERROR")'
```

## The Database

SQLite table with messages:

```sql
CREATE TABLE messages (
    message_id TEXT PRIMARY KEY,
    from_msisdn TEXT NOT NULL,
    to_msisdn TEXT NOT NULL,
    ts TEXT NOT NULL,
    text TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_messages_ts ON messages(ts ASC, message_id ASC);
CREATE INDEX idx_messages_from ON messages(from_msisdn);
```

**Why this design:**
- `message_id` is the main key (stops duplicates)
- Index on `from_msisdn` for quick filtering by sender
- Index on `ts` for fast sorting by time
- All timestamps are ISO-8601 with Z

## How I built this

### Why HMAC signatures?
- Uses HMAC-SHA256 on the request body
- Signature goes in `X-Signature` header as hex
- Bad signature = 401 error, nothing stored
- Secret comes from `WEBHOOK_SECRET` env var

### Why no duplicates?
- Message ID is unique (database enforces this)
- Send the same message twice = still 200 OK (idempotent)
- Just doesn't store it again
- Logged internally but doesn't break the request

### Pagination
- Default gets 50 per page, max 100
- Ordered by timestamp then message ID (always same order)
- Total count is all matching records, not just this page

### Stats endpoint
- Just SQL aggregates, no fancy stuff
- Top 10 senders by count
- First and last message timestamps

### Metrics
- Stores in memory with locks
- Tracks each endpoint and status code
- Records webhook results
- Histograms for latency

## Running Locally

```bash
# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Get packages
pip install -r requirements.txt

# Set it up
export WEBHOOK_SECRET="test-secret"
export DATABASE_URL="sqlite:///./app.db"

# Start it
python -m uvicorn app.main:app --reload

# Tests
pytest tests/
```

## Test commands

```bash
# Everything
make test

# One test file
make test-webhook
make test-messages
make test-stats

# With pytest directly
pytest tests/ -v
pytest tests/test_webhook.py -v
```

## Make commands

```bash
make help         # What can I do?
make up          # Start it
make down        # Stop it
make logs        # Watch logs
make test        # Run tests
make clean       # Delete everything
make health      # Check health
```

## Quick Examples

### Send a message

```bash
BODY='{"message_id":"test1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello World"}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "your-secret" -hex | sed 's/^.* //')

curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
```

### Look at the database

```bash
# From your computer
sqlite3 ./data/app.db "SELECT * FROM messages;"

# From inside the container
docker compose exec api sqlite3 /data/app.db "SELECT * FROM messages LIMIT 5;"
```

### Check the schema

```bash
docker compose exec api sqlite3 /data/app.db ".schema"
```

## Problems?

### /health/ready says 503
- Check WEBHOOK_SECRET is set: `docker compose exec api env | grep WEBHOOK_SECRET`
- Check DB: `docker compose exec api sqlite3 /data/app.db "SELECT 1 FROM messages LIMIT 1;"`

### /webhook gives 401
- Make sure signature is right: `echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -hex`
- Using same secret as at startup?
- JSON not getting messed up?

### No logs
- Is LOG_LEVEL set? (default INFO)
- Check: `docker compose logs api`
- JSON logging should work by default

### Database locked
- SQLite locks sometimes, just wait
- One writer at a time
- Use PostgreSQL if you need high concurrency

## How fast is it?

- SQLite handles ~1,000 messages/sec
- Multiple readers at once, but only one writer
- Indexes on sender and timestamp are fast
- Metrics stored in memory (good for <1M requests/min)
- To go bigger, use PostgreSQL and load balance

## What I used

- VS Code
- Python 3.11
- FastAPI 0.104
- pytest
- Docker and Docker Compose

## License

MIT

## Questions?

For issues:
1. Check the troubleshooting above
2. Look at logs: `docker compose logs api`
3. Check env variables are right
4. Look at the design section above to understand why things work this way

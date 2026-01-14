"""
Webhook API - handles WhatsApp-like messages with signature verification.
"""
import hashlib
import hmac
import re
import time
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Query, Header
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field, validator

from app.config import config
from app.models import init_db, check_db_health
from app.storage import MessageStorage
from app.logging_utils import setup_logging, get_logger, LogContext, create_request_id
from app.metrics import get_metrics


# Models for requests/responses

class MessageRequest(BaseModel):
    """Incoming message"""
    message_id: str = Field(..., min_length=1)
    from_msisdn: str = Field(..., alias="from")
    to_msisdn: str = Field(..., alias="to")
    ts: str = Field(...)
    text: Optional[str] = Field(None, max_length=4096)
    
    @validator("from_msisdn", pre=True)
    def validate_from(cls, v):
        if not isinstance(v, str):
            raise ValueError("from must be a string")
        if not re.match(r'^\+\d+$', v):
            raise ValueError("from must be in E.164 format (+ followed by digits)")
        return v
    
    @validator("to_msisdn")
    def validate_to(cls, v):
        if not re.match(r'^\+\d+$', v):
            raise ValueError("to must be in E.164 format (+ followed by digits)")
        return v
    
    @validator("ts")
    def validate_ts(cls, v):
        # Must be ISO-8601 UTC with Z suffix
        if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$', v):
            raise ValueError("ts must be ISO-8601 UTC format with Z suffix")
        return v
    
    class Config:
        populate_by_name = True
        by_alias = True


class WebhookResponse(BaseModel):
    """Webhook response."""
    status: str


class MessageData(BaseModel):
    """Single message in listing."""
    message_id: str
    from_msisdn: str = Field(alias="from")
    to_msisdn: str = Field(alias="to")
    ts: str
    text: Optional[str] = None
    
    class Config:
        populate_by_name = True


class MessagesResponse(BaseModel):
    """Paginated messages response."""
    data: list[dict]
    total: int
    limit: int
    offset: int


class StatsResponse(BaseModel):
    """Analytics statistics response."""
    total_messages: int
    senders_count: int
    messages_per_sender: list[dict]
    first_message_ts: Optional[str]
    last_message_ts: Optional[str]


# ============================================================================
# Application Initialization
# ============================================================================

logger = None
log_context = None
metrics = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup/shutdown"""
    global logger, log_context, metrics
    
    # Start
    init_db()
    logger = setup_logging()
    log_context = LogContext(logger)
    metrics = get_metrics()
    
    logger.info("Application startup complete")
    
    yield
    
    # Stop
    logger.info("Application shutdown")


# Create the app
app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description=config.API_DESCRIPTION,
    lifespan=lifespan,
)


# Middleware to track requests and timing

@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    """Track how long requests take"""
    request_id = create_request_id()
    request.state.request_id = request_id
    
    start_time = time.time()
    response = await call_next(request)
    latency_ms = (time.time() - start_time) * 1000
    
    # Save metrics
    metrics.record_http_request(request.url.path, response.status_code)
    metrics.record_latency(latency_ms)
    
    # Log it
    log_context.log_request(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=round(latency_ms, 2),
    )
    
    return response


# Endpoints

@app.post("/webhook")
async def webhook(
    request: Request,
    body: MessageRequest,
    x_signature: str = Header(None),
):
    """
    Ingest WhatsApp-like messages with HMAC signature verification.
    """
    request_id = request.state.request_id
    start_time = time.time()
    
    try:
        message_id = body.message_id
        
        # Get raw body for signature verification
        raw_body = await request.body()
        
        # Verify HMAC signature
        if not x_signature:
            metrics.record_webhook_result("invalid_signature")
            log_context.log_webhook(
                request_id=request_id,
                message_id=message_id,
                is_duplicate=False,
                result="invalid_signature",
                status=401,
                latency_ms=round((time.time() - start_time) * 1000, 2),
            )
            raise HTTPException(
                status_code=401,
                detail="invalid signature",
            )
        
        # Compute expected signature
        secret = config.WEBHOOK_SECRET.encode()
        expected_signature = hmac.new(
            secret,
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        
        if not hmac.compare_digest(x_signature, expected_signature):
            metrics.record_webhook_result("invalid_signature")
            log_context.log_webhook(
                request_id=request_id,
                message_id=message_id,
                is_duplicate=False,
                result="invalid_signature",
                status=401,
                latency_ms=round((time.time() - start_time) * 1000, 2),
            )
            raise HTTPException(
                status_code=401,
                detail="invalid signature",
            )
        
        # Check if message already exists (idempotency)
        is_duplicate = MessageStorage.message_exists(message_id)
        
        if is_duplicate:
            metrics.record_webhook_result("duplicate")
            log_context.log_webhook(
                request_id=request_id,
                message_id=message_id,
                is_duplicate=True,
                result="duplicate",
                status=200,
                latency_ms=round((time.time() - start_time) * 1000, 2),
            )
            return JSONResponse(
                status_code=200,
                content={"status": "ok"},
            )
        
        # Insert into database
        from_msisdn = body.from_msisdn
        success, error = MessageStorage.insert_message(
            message_id=message_id,
            from_msisdn=from_msisdn,
            to_msisdn=body.to_msisdn,
            ts=body.ts,
            text=body.text,
        )
        
        if success:
            metrics.record_webhook_result("created")
            log_context.log_webhook(
                request_id=request_id,
                message_id=message_id,
                is_duplicate=False,
                result="created",
                status=200,
                latency_ms=round((time.time() - start_time) * 1000, 2),
            )
            return JSONResponse(
                status_code=200,
                content={"status": "ok"},
            )
        else:
            metrics.record_webhook_result("duplicate")
            log_context.log_webhook(
                request_id=request_id,
                message_id=message_id,
                is_duplicate=True,
                result="duplicate",
                status=200,
                latency_ms=round((time.time() - start_time) * 1000, 2),
            )
            return JSONResponse(
                status_code=200,
                content={"status": "ok"},
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        metrics.record_webhook_result("validation_error")
        raise HTTPException(
            status_code=422,
            detail=str(e),
        )


@app.get("/messages")
async def get_messages(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    from_param: Optional[str] = Query(None, alias="from"),
    since: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
):
    """
    List stored messages with pagination and filtering.
    """
    messages, total = MessageStorage.get_messages(
        limit=limit,
        offset=offset,
        from_msisdn=from_param,
        since=since,
        q=q,
    )
    
    # Convert to response format
    data = []
    for msg in messages:
        data.append({
            "message_id": msg["message_id"],
            "from": msg["from_msisdn"],
            "to": msg["to_msisdn"],
            "ts": msg["ts"],
            "text": msg["text"],
        })
    
    return MessagesResponse(
        data=data,
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/stats")
async def get_stats():
    """
    Get analytical statistics about messages.
    """
    stats = MessageStorage.get_stats()
    
    # Convert per-sender format
    messages_per_sender = [
        {"from": item["from"], "count": item["count"]}
        for item in stats["messages_per_sender"]
    ]
    
    return StatsResponse(
        total_messages=stats["total_messages"],
        senders_count=stats["senders_count"],
        messages_per_sender=messages_per_sender,
        first_message_ts=stats["first_message_ts"],
        last_message_ts=stats["last_message_ts"],
    )


@app.get("/health/live")
async def health_live():
    """
    Liveness probe - returns 200 when app is running.
    """
    return JSONResponse(
        status_code=200,
        content={"status": "alive"},
    )


@app.get("/health/ready")
async def health_ready():
    """
    Readiness probe - returns 200 only if DB is healthy and WEBHOOK_SECRET is set.
    """
    # Check if WEBHOOK_SECRET is set
    is_valid, error_msg = config.validate()
    if not is_valid:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "reason": error_msg},
        )
    
    # Check database health
    if not check_db_health():
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "reason": "database not ready"},
        )
    
    return JSONResponse(
        status_code=200,
        content={"status": "ready"},
    )


@app.get("/metrics")
async def get_metrics_endpoint():
    """
    Expose Prometheus-style metrics.
    """
    prometheus_metrics = metrics.get_prometheus_metrics()
    return PlainTextResponse(
        content=prometheus_metrics,
        media_type="text/plain; charset=utf-8",
    )


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

"""Production AI agent for Part 6 lab complete."""
import json
import logging
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import estimate_cost_usd, enforce_monthly_budget, month_key
from app.rate_limiter import enforce_rate_limit
from utils.mock_llm import ask as llm_ask


logging.basicConfig(level=logging.INFO, format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}')
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_is_draining = False
_request_count = 0
_redis_client: redis.Redis | None = None


class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    model: str
    month_spend_usd: float
    timestamp: str


def _json_log(event: str, **kwargs):
    payload = {"event": event, **kwargs}
    logger.info(json.dumps(payload, ensure_ascii=True))


def get_redis() -> redis.Redis:
    if _redis_client is None:
        raise HTTPException(status_code=503, detail="Redis is not available")
    return _redis_client


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _is_ready, _redis_client
    _json_log("startup", app=settings.app_name, version=settings.app_version, redis_url=settings.redis_url)
    _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    _redis_client.ping()
    _is_ready = True
    _json_log("ready")
    try:
        yield
    finally:
        _is_ready = False
        if _redis_client is not None:
            _redis_client.close()
        _json_log("shutdown")


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count
    start = time.time()
    _request_count += 1

    if _is_draining and request.url.path not in ["/health", "/ready"]:
        return Response(
            status_code=503,
            content=json.dumps({"detail": "Server is shutting down"}),
            media_type="application/json",
        )

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"

    elapsed_ms = round((time.time() - start) * 1000, 1)
    _json_log("request", method=request.method, path=request.url.path, status=response.status_code, ms=elapsed_ms)
    return response


def _history_key(user_id: str) -> str:
    return f"history:{user_id}"


def _spend_key(user_id: str, period: str) -> str:
    return f"cost:{user_id}:{period}"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "container": True,
    }


@app.get("/ready")
def ready(r: redis.Redis = Depends(get_redis)):
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Not ready")
    try:
        r.ping()
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis not ready") from exc
    return {"status": "ready"}


@app.post("/ask", response_model=AskResponse)
def ask_agent(body: AskRequest, request: Request, _api_key: str = Depends(verify_api_key), r: redis.Redis = Depends(get_redis)):
    enforce_rate_limit(r, body.user_id, settings.rate_limit_per_minute, 60)

    history_key = _history_key(body.user_id)
    history = r.lrange(history_key, -10, -1)
    context = "\n".join(history)
    prompt = body.question if not context else f"Previous conversation:\n{context}\n\nUser: {body.question}"

    estimated_cost = estimate_cost_usd(body.question, "")
    enforce_monthly_budget(r, body.user_id, estimated_cost, settings.monthly_budget_usd)

    answer = llm_ask(prompt)
    actual_cost = estimate_cost_usd(body.question, answer)
    spend_key = _spend_key(body.user_id, month_key())
    month_spend = r.incrbyfloat(spend_key, actual_cost)
    r.expire(spend_key, 35 * 24 * 3600)

    r.rpush(history_key, f"user:{body.question}", f"assistant:{answer}")
    r.ltrim(history_key, -20, -1)
    r.expire(history_key, 7 * 24 * 3600)

    _json_log(
        "agent_call",
        user_id=body.user_id,
        question_len=len(body.question),
        client=str(request.client.host) if request.client else "unknown",
        month_spend_usd=round(float(month_spend), 6),
    )

    return AskResponse(
        user_id=body.user_id,
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        month_spend_usd=round(float(month_spend), 6),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _handle_sigterm(signum, _frame):
    global _is_draining
    _is_draining = True
    _json_log("signal", signal="SIGTERM", signum=signum)


signal.signal(signal.SIGTERM, _handle_sigterm)


if __name__ == "__main__":
    _json_log("boot", host=settings.host, port=settings.port, environment=settings.environment)
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )

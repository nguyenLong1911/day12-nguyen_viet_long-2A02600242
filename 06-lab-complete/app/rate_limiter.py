"""Redis-backed sliding window rate limiter."""
import time

import redis
from fastapi import HTTPException


def enforce_rate_limit(r: redis.Redis, user_id: str, max_requests: int, window_seconds: int = 60) -> None:
    now = time.time()
    key = f"ratelimit:{user_id}"
    window_start = now - window_seconds

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    _, current_count = pipe.execute()

    if int(current_count) >= max_requests:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {max_requests} requests/{window_seconds}s",
            headers={"Retry-After": str(window_seconds)},
        )

    member = f"{now}:{user_id}"
    pipe = r.pipeline()
    pipe.zadd(key, {member: now})
    pipe.expire(key, window_seconds + 5)
    pipe.execute()

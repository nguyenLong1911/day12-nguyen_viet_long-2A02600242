"""Monthly budget guard using Redis."""
from datetime import datetime

import redis
from fastapi import HTTPException


def month_key() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def estimate_cost_usd(question: str, answer: str) -> float:
    # Simple token estimate for lab purposes.
    input_tokens = max(1, len(question.split()) * 2)
    output_tokens = max(1, len(answer.split()) * 2)
    return (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006


def enforce_monthly_budget(r: redis.Redis, user_id: str, estimated_cost: float, monthly_budget_usd: float) -> None:
    key = f"cost:{user_id}:{month_key()}"
    current = float(r.get(key) or 0.0)
    if current + estimated_cost > monthly_budget_usd:
        raise HTTPException(status_code=402, detail="Monthly budget exceeded")

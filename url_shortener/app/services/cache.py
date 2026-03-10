import json

import redis

from app.core.config import settings


redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def get_cached_original_url(short_code: str) -> str | None:
    return redis_client.get(f"link:{short_code}")


def set_cached_original_url(short_code: str, original_url: str, ttl_seconds: int = 3600) -> None:
    redis_client.setex(f"link:{short_code}", ttl_seconds, original_url)


def delete_cached_original_url(short_code: str) -> None:
    redis_client.delete(f"link:{short_code}")


def get_cached_stats(short_code: str) -> dict | None:
    raw = redis_client.get(f"stats:{short_code}")
    if not raw:
        return None
    return json.loads(raw)


def set_cached_stats(short_code: str, payload: dict, ttl_seconds: int = 300) -> None:
    redis_client.setex(f"stats:{short_code}", ttl_seconds, json.dumps(payload, default=str))


def delete_cached_stats(short_code: str) -> None:
    redis_client.delete(f"stats:{short_code}")

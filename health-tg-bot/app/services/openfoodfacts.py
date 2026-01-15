from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import aiohttp

@dataclass(frozen=True)
class FoodInfo:
    name: str
    kcal_per_100g: float
    code: str | None = None
    source: str = "OpenFoodFacts"

def _pick_name(p: dict[str, Any]) -> str:
    return (
        p.get("product_name_ru")
        or p.get("product_name")
        or p.get("generic_name_ru")
        or p.get("generic_name")
        or "Продукт"
    ).strip()

def _pick_kcal_per_100g(p: dict[str, Any]) -> float | None:
    nutr = p.get("nutriments") or {}
    v = nutr.get("energy-kcal_100g")
    if isinstance(v, (int, float)) and v > 0:
        return float(v)
    e = nutr.get("energy_100g")
    if isinstance(e, (int, float)) and e > 0:
        e = float(e)
        if e <= 1000:
            return e
        return e * 0.239005736
    return None

async def search_food_candidates(
    session: aiohttp.ClientSession,
    *,
    query: str,
    user_agent: str,
    page_size: int = 10,
    limit: int = 5,
    timeout_s: float = 6.0
) -> list[FoodInfo]:
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": page_size,
        "fields": "code,product_name,product_name_ru,generic_name,generic_name_ru,nutriments",
    }
    headers = {"User-Agent": user_agent}
    timeout = aiohttp.ClientTimeout(total=timeout_s)

    async with session.get(url, params=params, headers=headers) as resp:
        resp.raise_for_status()
        data = await resp.json()

    out: list[FoodInfo] = []
    for p in (data.get("products") or []):
        kcal = _pick_kcal_per_100g(p)
        if kcal is None:
            continue
        out.append(
            FoodInfo(
                name=_pick_name(p),
                kcal_per_100g=round(float(kcal), 2),
                code=str(p.get("code")) if p.get("code") else None,
            )
        )
        if len(out) >= limit:
            break

    return out




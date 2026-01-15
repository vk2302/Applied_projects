from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp


@dataclass(frozen=True)
class WeatherInfo:
    temp_c: float
    city: str


async def get_current_temp_c_by_city(
    session: aiohttp.ClientSession,
    *,
    city: str,
    api_key: str,
) -> WeatherInfo:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "metric"}

    async with session.get(url, params=params) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise RuntimeError(f"OpenWeather error {resp.status}: {text[:200]}")
        data: dict[str, Any] = await resp.json()

    temp_c = float(data["main"]["temp"])
    city_name = str(data.get("name") or city)
    return WeatherInfo(temp_c=temp_c, city=city_name)


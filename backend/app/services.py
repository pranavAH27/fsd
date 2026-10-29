import math
import httpx
from fastapi import HTTPException
from .config import settings


def distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lng2-lng1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


async def geocode(address: str) -> dict:
    if not settings.google_maps_api_key:
        raise HTTPException(503, "Google Maps is not configured")
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get("https://maps.googleapis.com/maps/api/geocode/json", params={"address": address, "key": settings.google_maps_api_key})
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "OK":
        raise HTTPException(422, "Address could not be geocoded")
    item = data["results"][0]
    loc = item["geometry"]["location"]
    return {"formatted_address": item["formatted_address"], "lat": loc["lat"], "lng": loc["lng"]}


async def ask_grok(message: str, history: list[dict]) -> str:
    if not settings.grok_api_key:
        raise HTTPException(503, "Grok assistant is not configured")
    messages = [{"role": "system", "content": "You are SurplusReach's practical food-safety and NGO logistics assistant. Give concise guidance, prioritize conservative food safety, distinguish general guidance from local regulations, and never assure that food is safe based on incomplete information. For unsafe temperatures or uncertain handling, advise discarding. Do not replace local health authority advice."}]
    messages.extend(history[-12:])
    messages.append({"role": "user", "content": message})
    async with httpx.AsyncClient(timeout=40) as client:
        response = await client.post("https://api.x.ai/v1/chat/completions", headers={"Authorization": f"Bearer {settings.grok_api_key}"}, json={"model": settings.grok_model, "messages": messages, "temperature": 0.3})
    if response.status_code >= 400:
        raise HTTPException(502, "Grok assistant request failed")
    return response.json()["choices"][0]["message"]["content"]

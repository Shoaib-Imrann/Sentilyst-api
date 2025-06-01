import os
import httpx
from fastapi import HTTPException
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")

async def fetch_ma_events(ticker: str, region: str = "US", lang: str = "en-US"):
    """
    Fetch M&A-related calendar events for a given ticker.

    Returns:
        dict: {"eventsData": [ {id, title, date, time, type}, ... ]}
    """
    url = f"https://{RAPIDAPI_HOST}/stock/get-events-calendar"
    params = {
        "tickersFilter": ticker,
        "region": region,
        "lang": lang,
        "modules": "ipoEvents,earnings,secReports"
    }
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json().get("finance", {}).get("result", {}).get("mixedEvents", [])

            events = []
            eid = 1
            for day in data:
                # Fallback timestamp for the day
                day_ts = day.get("timestamp")  # in milliseconds

                for rec in day.get("records", []):
                    # Prefer per-record filingDate, else fallback
                    ts = rec.get("filingDate") if rec.get("filingDate") is not None else day_ts
                    if ts is None:
                        continue  # skip records w/o any timestamp

                    # Convert ms timestamp to datetime
                    dt = datetime.fromtimestamp(ts / 1000)
                    date_str = dt.strftime("%b %-d, %Y")   # e.g. "Mar 11, 2025"
                    time_str = dt.strftime("%-I:%M %p")    # e.g. "12:00 AM"

                    title = f"{rec.get('companyName', '').strip()} {rec.get('type', '').strip()}"

                    events.append({
                        "id": eid,
                        "title": title,
                        "date": date_str,
                        "time": time_str,
                        "type": rec.get("type", "Other")
                    })
                    eid += 1

            return {"eventsData": events}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch calendar events: {e}")

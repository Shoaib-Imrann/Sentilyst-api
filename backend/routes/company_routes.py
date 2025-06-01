from fastapi import APIRouter, Query
from controllers.fininfo import fetch_ma_events

router = APIRouter(prefix="/calendar", tags=["Calendar"])

@router.get("/events")
async def get_calendar_events(
    ticker: str = Query(..., description="Ticker symbol, e.g., AMRN")
):
    return await fetch_ma_events(ticker)

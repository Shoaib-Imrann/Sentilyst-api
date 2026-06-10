from fastapi import APIRouter, Request
from controllers import news_controller
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/news", tags=["News"])
limiter = Limiter(key_func=get_remote_address)

@router.get("/fetch-ma-news")
@limiter.limit("5/minute")
async def fetch_news(request: Request):
    return await news_controller.fetch_ma_news()

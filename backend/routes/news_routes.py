from fastapi import APIRouter
from controllers import news_controller

router = APIRouter(prefix="/news", tags=["News"])

router.get("/fetch-ma-news")(news_controller.fetch_ma_news)

from fastapi import APIRouter, Request
from controllers import sentiment_controller
from models.requests import SentimentAnalysisRequest
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(tags=["Analyze"])
limiter = Limiter(key_func=get_remote_address)

@router.post("/analyze")
@limiter.limit("10/minute")
async def analyze(request: Request, data: SentimentAnalysisRequest):
    return await sentiment_controller.analyze_sentiment(data)


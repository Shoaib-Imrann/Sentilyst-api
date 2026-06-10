from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes import sentiment_routes
from routes import news_routes
from middleware.security import SecurityHeadersMiddleware, RequestSizeLimiterMiddleware
from middleware.security_logger import SecurityEventLogger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("sentilyst")

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address, default_limits=["100/hour"])
app = FastAPI(docs_url="/docs", redoc_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Global exception handler - prevent stack trace leaks
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."}
    )

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Sentilyst API...")
    logger.info(f"CORS Origins: {os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173')}")
    from services.sentiment_analysis import warmup_model
    warmup_model()
    logger.info("API ready.")

# CORS Configuration - configurable via environment
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
if cors_origins == "*":
    origins = ["*"]
else:
    origins = [origin.strip() for origin in cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Security middleware
app.add_middleware(SecurityEventLogger)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimiterMiddleware, max_size=1024 * 1024)  # 1MB limit

app.include_router(sentiment_routes.router, prefix="/api")
app.include_router(news_routes.router, prefix="/api")

@app.get("/")
@limiter.limit("30/minute")
def root(request: Request):
    return {"message": "Sentilyst API - Sentiment Analysis Service", "status": "healthy"}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)

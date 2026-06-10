from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from models.requests import SentimentAnalysisRequest
from services.scraper import scrape_google_news, scrape_newsapi
from services.sentiment_analysis import analyze_batch
from services.cache import get_sentiment_cache, set_sentiment_cache
import time
import logging
from datetime import datetime

logger = logging.getLogger("sentilyst")
logger.setLevel(logging.INFO)


async def analyze_sentiment(request_data: SentimentAnalysisRequest):
    t0 = time.time()
    
    query = request_data.query
    logger.info(f"Processing sentiment analysis for query: {query[:50]}...")

    # Check cache first
    cached_result = get_sentiment_cache(query)
    if cached_result:
        logger.info(f"Returning cached result for query: {query[:50]}...")
        cached_result["cached"] = True
        cached_result["cache_retrieval_time"] = round(time.time() - t0, 3)
        return JSONResponse(cached_result)

    try:
        # 1) Scraping
        google_data = scrape_google_news(query)
        newsapi_data = scrape_newsapi(query)
        scraped_data = google_data + newsapi_data
        t1 = time.time()
        logger.info(
            "Scraped %s Google News + %s NewsAPI articles",
            len(google_data),
            len(newsapi_data),
        )

        # 2) Preprocess - cap at 30 items and truncate text
        scraped_data_capped = scraped_data[:30]
        texts = [item["title"][:500] for item in scraped_data_capped]
        t2 = time.time()
        
        # 3) Model inference
        results = analyze_batch(texts)
        t3 = time.time()
        
        # 4) Aggregation
        sentiment_count = {"positive": 0, "neutral": 0, "negative": 0}
        sentiment_confidences = {"positive": [], "neutral": [], "negative": []}
        for label, conf in results:
            key = label.lower()
            sentiment_count[key] += 1
            sentiment_confidences[key].append(conf)
        
        total = sum(sentiment_count.values()) or 1
        sentiment_percentages = {
            k: round(v / total * 100, 2) for k, v in sentiment_count.items()
        }
        t4 = time.time()
        
        logger.info(f"Successfully processed query in {round(t4 - t0, 2)}s")
        
        result = {
            "query": query,
            "scraped_data": scraped_data,
            "source_counts": {
                "google_news": len(google_data),
                "newsapi": len(newsapi_data),
            },
            "sentiment_count": sentiment_count,
            "sentiment_percentages": sentiment_percentages,
            "created_at": datetime.now().isoformat(),
            "processing_time": round(t4 - t0, 2),
            "cached": False
        }
        
        # Cache the result
        set_sentiment_cache(query, result)
        
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Error processing sentiment analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing your request")

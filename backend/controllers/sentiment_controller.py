# controllers/sentiment_controller.py
from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from services.scraper import scrape_reddit, scrape_google_news
from services.sentiment_analysis import analyze_batch, calculate_risk
from supabase import create_client, Client
import os
import time
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("sentilyst")
logger.setLevel(logging.INFO)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


async def analyze_sentiment(request: Request):
    t0 = time.time()
    # logger.info("Request started")
    
    data = await request.json()
    query = data.get("query")
    if not query:
        raise HTTPException(status_code=422, detail="Field 'query' is required")

    user = getattr(request.state, "user", None)

    # 1) Scraping
    reddit_data = scrape_reddit(query)
    google_data = scrape_google_news(query)
    scraped_data = reddit_data + google_data
    t1 = time.time()
    # logger.info(f"SCRAPING TOOK: {t1 - t0:.2f}s | Reddit: {len(reddit_data)} | Google News: {len(google_data)} | Total: {len(scraped_data)}")

    # 2) Preprocess - cap at 30 items and truncate text
    scraped_data_capped = scraped_data[:30]
    texts = [(post.split(" - ", 1)[0] if " - " in post else post)[:500] for post in scraped_data_capped]
    t2 = time.time()
    # logger.info(f"PREPROCESS TOOK: {t2 - t1:.2f}s | Processed {len(texts)} items")
    
    # 3) Model inference
    results = analyze_batch(texts)
    t3 = time.time()
    # logger.info(f"MODEL INFERENCE TOOK: {t3 - t2:.2f}s")
    
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
    risk_level = calculate_risk(sentiment_percentages, sentiment_confidences)
    t4 = time.time()
    # logger.info(f"AGGREGATION TOOK: {t4 - t3:.2f}s")

    # 5) DB/Storage
    if user:
        ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
        insert_data = {
            "user_id": user,
            "query": query,
            "positive": sentiment_percentages.get("positive", 0.0),
            "negative": sentiment_percentages.get("negative", 0.0),
            "reddit_count": len(reddit_data),
            "google_news_count": len(google_data),
            "total_results": len(scraped_data),
            "risk_level": risk_level,
            "created_at": ist_time.isoformat(),
        }
        res = supabase.table("analyzed_data").insert(insert_data).execute()
        if res.data is None:
            raise HTTPException(status_code=500, detail="Supabase insert failed")
        saved_created_at = insert_data["created_at"]
    else:
        saved_created_at = datetime.now().date().isoformat()
    t5 = time.time()
    # logger.info(f"DB SAVE TOOK: {t5 - t4:.2f}s")
    # logger.info(f"TOTAL REQUEST TIME: {t5 - t0:.2f}s")
    
    return JSONResponse({
        "query": query,
        "scraped_data": scraped_data,
        "sentiment_count": sentiment_count,
        "sentiment_percentages": sentiment_percentages,
        "risk_level": risk_level,
        "created_at": saved_created_at,
        "saved": bool(user)
    })



async def get_user_analysis(request: Request):
    user = request.state.user

    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        response = supabase.table("analyzed_data").select("*").eq("user_id", user).order("created_at", desc=True).execute()

        if response.data is None or len(response.data) == 0:
            raise HTTPException(status_code=404, detail="No data found for the user")
       # Return only the sexy fields you need
        filtered_data = [
            {
                "id": item.get("id"),
                "query": item.get("query"),
                "google_news_count": item.get("google_news_count"),
                "reddit_count": item.get("reddit_count"),
                "total_results": item.get("total_results"),
                "positive": item.get("positive"),
                "negative": item.get("negative"),
                "risk_level": item.get("risk_level"),
                "created_at": item.get("created_at"),
            }
            for item in response.data
        ]

        return JSONResponse(content={"data": filtered_data})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    

async def delete_analysis(request: Request, id: str):
    user_id = request.state.user
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Fetch the record
    response = supabase.from_("analyzed_data") \
        .select("*") \
        .eq("id", id) \
        .eq("user_id", user_id) \
        .execute()

    if not response.data:  # no rows found
        raise HTTPException(status_code=404, detail="Item not found")

    # Perform deletion
    delete_response = supabase.from_("analyzed_data") \
        .delete() \
        .eq("id", id) \
        .eq("user_id", user_id) \
        .execute()

    # If deletion didn’t return deleted rows, something broke
    if not delete_response.data:
        raise HTTPException(status_code=500, detail="Supabase delete failed")

    return {"message": "Deleted"}

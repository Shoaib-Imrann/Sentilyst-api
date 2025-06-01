# controllers/sentiment_controller.py
from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from services.scraper import scrape_reddit, scrape_google_news
from services.sentiment_analysis import analyze_text, calculate_risk
from supabase import create_client, Client
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


async def analyze_sentiment(request: Request):
    data = await request.json()
    query = data.get("query")
    if not query:
        raise HTTPException(status_code=422, detail="Field 'query' is required")

    user = getattr(request.state, "user", None)

    reddit_data = scrape_reddit(query)
    google_data = scrape_google_news(query)
    # reuters_data = scrape_reuters(query)
    scraped_data = reddit_data + google_data 

    sentiment_count = {"positive": 0, "neutral": 0, "negative": 0}
    sentiment_confidences = {"positive": [], "neutral": [], "negative": []}
    for post in scraped_data:
        text, _ = post.split(" - ", 1) if " - " in post else (post, "")
        label, conf = analyze_text(text)
        key = label.lower()
        sentiment_count[key] += 1
        sentiment_confidences[key].append(conf)

    total = sum(sentiment_count.values()) or 1
    sentiment_percentages = {
        k: round(v / total * 100, 2) for k, v in sentiment_count.items()
    }

    risk_level = calculate_risk(sentiment_percentages, sentiment_confidences)

    if user:
        # Get current time and convert to IST (UTC+5:30)
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

        if res.data is None:  # Check if data is None, indicating an error
            raise HTTPException(status_code=500, detail="Supabase insert failed")
            
        # Use the created_at value that was saved to the database
        saved_created_at = insert_data["created_at"]
    else:
        # If not logged in, just use current date
        saved_created_at = datetime.now().date().isoformat()
    
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

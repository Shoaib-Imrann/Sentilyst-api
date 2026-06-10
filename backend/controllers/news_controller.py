from fastapi import HTTPException
from pydantic import BaseModel
import httpx
import os
from typing import Optional, List
from dotenv import load_dotenv
import re
import logging
from services.cache import get_news_cache, set_news_cache

load_dotenv()

logger = logging.getLogger("sentilyst")

class NewsArticle(BaseModel):
    title: str
    description: Optional[str] = None
    url: str
    publishedAt: str
    source: str
    urlToImage: Optional[str] = None
    category: str

class CategoryNews(BaseModel):
    all: List[NewsArticle]
    technology: List[NewsArticle]
    finance: List[NewsArticle]
    retail: List[NewsArticle]
    other: List[NewsArticle]

# Function to categorize news articles based on content
def categorize_article(title, description):
    title_lower = title.lower() if title else ""
    desc_lower = description.lower() if description else ""
    text = f"{title_lower} {desc_lower}"
    
    categories = {
        "technology": ["tech", "software", "digital", "cloud", "online", "internet", "ai", 
                      "artificial intelligence", "saas", "platform", "app", "semiconductor", 
                      "computing", "cybersecurity", "data", "it ", "telecom"],
        
        "finance": ["bank", "financ", "invest", "capital", "fund", "asset", "wealth", 
                   "insurance", "loan", "credit", "payment", "fintech", "trading"],
        
        "retail": ["retail", "store", "consumer", "shop", "brand", "e-commerce", "ecommerce", 
                  "merchandise", "product", "fashion", "food", "grocery", "chain"]
    }
    
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in text:
                return category
    
    return "other"

async def fetch_ma_news():
    # Check cache first
    cached_result = get_news_cache()
    if cached_result:
        logger.info("Returning cached M&A news")
        return cached_result
    
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        logger.warning("News API key not configured")
        raise HTTPException(status_code=503, detail="News API is not configured. Please set NEWSAPI_KEY environment variable.")

    params = {
        "q": '(merger OR acquisition OR "M&A" OR takeover OR "buys out" OR "acquires")',
        "language": "en",
        "pageSize": 100,
        "apiKey": api_key
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            logger.info("Fetching M&A news from NewsAPI")
            response = await client.get("https://newsapi.org/v2/everything", params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'ok':
                articles = data.get('articles', [])
                
                categorized_news = {
                    "all": [],
                    "technology": [],
                    "finance": [],
                    "retail": [],
                    "other": []
                }
                
                for article in articles:
                    title = article.get('title', '')
                    description = article.get('description', '')
                    
                    ma_terms = r"merger|acquisition|acquire[sd]?|takeover|buy[s]? out|deal|combines with"
                    if re.search(ma_terms, f"{title} {description}".lower()):
                        article_category = categorize_article(title, description)
                        
                        news_article = {
                            "title": title,
                            "description": description,
                            "url": article['url'],
                            "publishedAt": article['publishedAt'],
                            "source": article['source']['name'] if article['source'] and 'name' in article['source'] else '',
                            "urlToImage": article.get('urlToImage'),
                            "category": article_category
                        }
                        
                        categorized_news["all"].append(news_article)
                        categorized_news[article_category].append(news_article)
                
                logger.info(f"Successfully fetched {len(categorized_news['all'])} M&A articles")
                
                # Cache the result
                set_news_cache(categorized_news)
                
                return categorized_news
            else:
                logger.error(f"NewsAPI returned non-ok status: {data.get('status')}")
                raise HTTPException(status_code=500, detail="Failed to fetch news from NewsAPI")
        except httpx.TimeoutException:
            logger.error("Timeout while fetching news from NewsAPI")
            raise HTTPException(status_code=504, detail="News API request timed out")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from NewsAPI: {e.response.status_code}")
            raise HTTPException(status_code=502, detail="News API returned an error")
        except Exception as e:
            logger.error(f"Unexpected error fetching news: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="An error occurred while fetching news")

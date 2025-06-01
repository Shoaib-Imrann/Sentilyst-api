from fastapi import HTTPException
from pydantic import BaseModel
import httpx
import os
from typing import Optional, List
from dotenv import load_dotenv
import re

load_dotenv()

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
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API key not found in environment variables.")

    params = {
        "q": '(merger OR acquisition OR "M&A" OR takeover OR "buys out" OR "acquires")',
        "language": "en",
        "pageSize": 100,
        "apiKey": api_key
    }

    async with httpx.AsyncClient() as client:
        try:
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
                
                return categorized_news
            else:
                raise HTTPException(status_code=500, detail="Failed to fetch news from NewsAPI.")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Request error: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

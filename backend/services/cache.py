from cachetools import TTLCache
import hashlib
import json
import logging

logger = logging.getLogger("sentilyst.cache")

# In-memory caches with TTL (Time To Live)
# Sentiment: 1 hour cache, max 1000 entries
sentiment_cache = TTLCache(maxsize=1000, ttl=3600)

# News: 30 minutes cache, max 100 entries
news_cache = TTLCache(maxsize=100, ttl=1800)

def get_cache_key(data: dict) -> str:
    """Generate consistent cache key from dict"""
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.md5(json_str.encode()).hexdigest()

def get_sentiment_cache(query: str):
    """Get cached sentiment analysis result"""
    cache_key = get_cache_key({"query": query.lower().strip()})
    result = sentiment_cache.get(cache_key)
    if result:
        logger.info(f"Cache HIT for sentiment query: {query[:50]}...")
    return result

def set_sentiment_cache(query: str, result: dict):
    """Cache sentiment analysis result"""
    cache_key = get_cache_key({"query": query.lower().strip()})
    sentiment_cache[cache_key] = result
    logger.info(f"Cache SET for sentiment query: {query[:50]}...")

def get_news_cache():
    """Get cached news results"""
    result = news_cache.get("ma_news")
    if result:
        logger.info("Cache HIT for M&A news")
    return result

def set_news_cache(result: dict):
    """Cache news results"""
    news_cache["ma_news"] = result
    logger.info("Cache SET for M&A news")

def clear_all_caches():
    """Clear all caches (useful for testing/admin)"""
    sentiment_cache.clear()
    news_cache.clear()
    logger.info("All caches cleared")

def get_cache_stats():
    """Get cache statistics"""
    return {
        "sentiment": {
            "size": len(sentiment_cache),
            "maxsize": sentiment_cache.maxsize,
            "ttl": sentiment_cache.ttl,
            "hits": sentiment_cache.currsize
        },
        "news": {
            "size": len(news_cache),
            "maxsize": news_cache.maxsize,
            "ttl": news_cache.ttl,
            "hits": news_cache.currsize
        }
    }

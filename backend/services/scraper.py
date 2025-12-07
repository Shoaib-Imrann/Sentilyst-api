import requests
from bs4 import BeautifulSoup
import feedparser
from urllib.parse import quote_plus

def scrape_reddit(query):
    headers = {"User-Agent": "SentilystBot/0.1 by imran"}
    url = f"https://www.reddit.com/search.json?q={query}&limit=50"
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        posts = res.json()["data"]["children"]
        results = [f"{p['data']['title']} - https://reddit.com{p['data']['permalink']}" for p in posts]
        print(f"Reddit scraped: {len(results)} posts")
        return results
    except Exception as e:
        print(f"Reddit scraping failed: {e}")
        return []

def scrape_google_news(query):
    encoded_query = quote_plus(f"{query} mergers acquisition")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(url)
        results = [f"{entry.title} - {entry.link}" for entry in feed.entries[:50]]
        print(f"Google News scraped: {len(results)} articles")
        return results
    except Exception as e:
        print(f"Google News scraping failed: {e}")
        return []

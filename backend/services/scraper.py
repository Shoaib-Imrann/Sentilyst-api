import requests
from bs4 import BeautifulSoup

def scrape_reddit(query):
    headers = {"User-Agent": "SentilystBot/0.1 by imran"}
    url = f"https://www.reddit.com/search.json?q={query}&limit=20"
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        posts = res.json()["data"]["children"]
        return [f"{p['data']['title']} - https://reddit.com{p['data']['permalink']}" for p in posts]
    except Exception as e:
        return [f"Failed to scrape Reddit: {e}"]

def scrape_google_news(query):
    headers = {"User-Agent": "SentilystBot/0.1 by imran"}
    url = f"https://news.google.com/search?q={query}+mergers+aquisition"
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        articles = soup.find_all('article')
        return [f"{article.find('a').text.strip()} - https://news.google.com{article.find('a')['href']}" for article in articles if article.find('a')]
    except Exception as e:
        return [f"Failed to scrape Google News: {e}"]

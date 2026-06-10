import os
import re
import logging
import requests
import feedparser
from datetime import datetime, timedelta
from urllib.parse import quote_plus

logger = logging.getLogger("sentilyst.scraper")

_MA_VERB = re.compile(
    r"\b(acquiring|acquires|acquired|buying|buys|buy|merger with|merging with|takeover of)\b",
    re.I,
)
_FILLER = re.compile(
    r"\b(acquiring|acquires|acquired|buying|buys|buy|merger|acquisition|deal|takeover|the|a|an|of|with|and)\b",
    re.I,
)
_SHOPPING_NOISE = re.compile(
    r"(\$\d|%\s*off|prime day|record low|low price|on sale|coupon|discount|"
    r"deal[s]? for|best buy|macbook|airpods|review:|hands[- ]on|james bond)",
    re.I,
)


def _extract_parties(query: str) -> tuple[str, str]:
    match = _MA_VERB.search(query)
    if not match:
        return "", ""

    buyer = _FILLER.sub(" ", query[: match.start()]).strip()
    buyer = " ".join(buyer.split())
    target = _FILLER.sub(" ", query[match.end() :]).strip()
    target = " ".join(target.split())
    return buyer, target


def _match_terms(query: str) -> dict:
    buyer, target = _extract_parties(query)
    phrases = []
    words = []

    if buyer:
        words.extend(w.lower() for w in buyer.split() if len(w) > 1)
    if target:
        phrases.append(target.lower())
        words.extend(w.lower() for w in target.split() if len(w) > 1)

    if not words:
        cleaned = _FILLER.sub(" ", query).strip()
        words = [w.lower() for w in cleaned.split() if len(w) > 2]

    return {
        "phrases": phrases,
        "words": list(dict.fromkeys(words)),
    }


def article_matches_query(title: str, description: str | None, query: str) -> bool:
    title = title or ""
    text = f"{title} {description or ''}".lower()

    if _SHOPPING_NOISE.search(title):
        return False

    terms = _match_terms(query)

    for phrase in terms["phrases"]:
        if phrase and phrase in text:
            return True

    significant = terms["words"]
    if not significant:
        return False

    return all(word in text for word in significant)


def scrape_google_news(query):
    encoded_query = quote_plus(f"{query} mergers acquisition")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(url)
        results = [
            {
                "title": entry.title,
                "url": entry.link,
                "source": "google_news",
            }
            for entry in feed.entries[:50]
            if entry.get("title") and entry.get("link")
        ]
        logger.info("Google News scraped: %s articles", len(results))
        return results
    except Exception as exc:
        logger.warning("Google News scraping failed: %s", exc)
        return []


def scrape_newsapi(query):
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key or api_key.strip() in {"", "your_api_key_here", "demo_key"}:
        logger.warning("NEWSAPI_KEY not configured; skipping NewsAPI scrape")
        return []

    buyer, target = _extract_parties(query)
    if buyer and target:
        api_q = f'"{buyer}" AND "{target}"'
    else:
        terms = _match_terms(query)["words"]
        if not terms:
            return []
        api_q = " AND ".join(terms[:4])

    params = {
        "q": api_q,
        "language": "en",
        "pageSize": 100,
        "sortBy": "relevancy",
        "searchIn": "title,description",
        "from": (datetime.utcnow() - timedelta(days=29)).strftime("%Y-%m-%d"),
        "apiKey": api_key,
    }

    try:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok":
            logger.warning("NewsAPI non-ok status: %s", data.get("status"))
            return []

        results = []
        seen_urls = set()
        for article in data.get("articles", []):
            title = article.get("title")
            url = article.get("url")
            description = article.get("description")

            if not title or not url or url in seen_urls:
                continue
            if not article_matches_query(title, description, query):
                continue

            seen_urls.add(url)
            results.append(
                {
                    "title": title,
                    "url": url,
                    "source": "newsapi",
                }
            )

        logger.info("NewsAPI scraped: %s matching articles", len(results))
        return results[:50]
    except Exception as exc:
        logger.warning("NewsAPI scraping failed: %s", exc)
        return []

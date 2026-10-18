import os
from datetime import date, timedelta

import requests

BASE_URL = "https://newsapi.org/v2"
TIMEOUT_SECONDS = 10    # FR-11
MAX_TECH_ITEMS = 20     # bulletin shows 5; give the model extra to choose from
MAX_FINANCE_ITEMS = 10
NEWS_WINDOW_DAYS = 2    # daily bulletin; 2 days because the free plan delays articles by 24 h


def _newsapi_get(endpoint: str, params: dict) -> dict:
    """Call a NewsAPI endpoint. Returns the JSON data, or {"error": "..."}."""
    api_key = os.environ.get("NEWS_API_KEY")
    if not api_key:
        return {"error": "NEWS_API_KEY is not set."}

    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            params=params,
            headers={"X-Api-Key": api_key},   # key in header, not in URL
            timeout=TIMEOUT_SECONDS,
        )
        data = response.json()
    except requests.Timeout:
        return {"error": f"NewsAPI timed out after {TIMEOUT_SECONDS} seconds."}
    except requests.RequestException:
        return {"error": "Could not connect to NewsAPI."}
    except ValueError:   # response is not JSON
        return {"error": f"NewsAPI returned an invalid response (HTTP {response.status_code})."}

    if data.get("status") != "ok":
        code = data.get("code", "unknownError")
        message = data.get("message", "No details.")
        return {"error": f"NewsAPI error ({code}): {message}"}
    return data


def _article_to_dict(article: dict) -> dict:
    """Convert a NewsAPI article into a simple dict for the model."""
    return {
        "title": article.get("title") or "",
        "source": (article.get("source") or {}).get("name") or "",
        "description": article.get("description") or "",
        "url": article.get("url") or "",
        "published": article.get("publishedAt") or "",
    }


def _is_usable(article: dict) -> bool:
    """Skip removed articles and articles without a URL."""
    return bool(article.get("url")) and article.get("title") != "[Removed]"


def get_tech_news(limit: int = 10) -> dict:
    """Get current technology headlines from major news sources via NewsAPI.

    Articles come from many outlets (e.g. The Verge, Wired, TechCrunch).
    There is no popularity ranking, so read the descriptions and pick
    the most important stories yourself. Always mention each story's source.

    Args:
        limit: How many headlines to return (1-20). Default is 10.

    Returns:
        A dict with "count" and "articles". Each article has title,
        source, description, url and published date.
        On failure, returns {"error": "..."} instead.
    """
    limit = max(1, min(limit, MAX_TECH_ITEMS))
    data = _newsapi_get(
        "top-headlines",
        {"country": "us", "category": "technology", "pageSize": MAX_TECH_ITEMS},
    )
    if "error" in data:
        return data

    articles = [_article_to_dict(a) for a in data.get("articles", []) if _is_usable(a)]
    articles = articles[:limit]
    return {"count": len(articles), "articles": articles}


def get_financial_news(companies: list[str], limit: int = 3) -> dict:
    """Get recent news about the given companies from the last 2 days.

    Search by short, common company names as they appear in headlines
    (e.g. "Apple", "Turkish Airlines"), not ticker symbols or legal names
    like "Apple Inc." or "Turk Hava Yollari Anonim Ortakligi".
    News for all companies is merged, duplicates are removed, and the
    newest articles come first. Each article says which company it is about.

    Args:
        companies: Company names to search for.
        limit: How many articles to return in total (1-10). Default is 3.

    Returns:
        A dict with "count" and "articles". Each article has company, title,
        source, description, url and published date. If some searches fail,
        an "errors" list names them; other results are still returned.
    """
    limit = max(1, min(limit, MAX_FINANCE_ITEMS))
    since = (date.today() - timedelta(days=NEWS_WINDOW_DAYS)).isoformat()
    articles = []
    errors = []
    seen_urls = set()

    for company in companies:
        data = _newsapi_get(
            "everything",
            {
                "q": f'"{company}"',          # quotes = exact phrase
                "searchIn": "title",          # company must be in the headline
                "from": since,
                "sortBy": "publishedAt",
                "pageSize": MAX_FINANCE_ITEMS,
            },
        )
        if "error" in data:
            errors.append(f"{company}: {data['error']}")
            continue

        for raw in data.get("articles", []):
            if not _is_usable(raw) or raw["url"] in seen_urls:
                continue
            seen_urls.add(raw["url"])
            articles.append({"company": company, **_article_to_dict(raw)})

    articles.sort(key=lambda a: a["published"], reverse=True)
    articles = articles[:limit]

    result = {"count": len(articles), "articles": articles}
    if errors:
        result["errors"] = errors
    return result


if __name__ == "__main__":
    # Quick manual test: python -m tools.news
    import json
    from dotenv import load_dotenv

    load_dotenv()
    print(json.dumps(get_tech_news(3), ensure_ascii=False, indent=2))
    print(json.dumps(get_financial_news(["Apple", "Turkish Airlines"], limit=5), ensure_ascii=False, indent=2))

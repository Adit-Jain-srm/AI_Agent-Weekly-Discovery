"""
search_agent.py: Handles all search engine logic, query construction, and aggregator/news filtering.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Set
from urllib.parse import urlparse, urlunparse

import aiohttp

from agents.config_agent import SERPER_API_KEY, SERPAPI_API_KEY
from config.constants import AGGREGATOR_DOMAINS, BATCH_SIZE, BASE_QUERIES


def normalize_url(url: str) -> str:
    """Normalize URL by removing query parameters and fragments for deduplication."""
    try:
        parsed = urlparse(url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    except Exception as e:
        logging.warning(f"Failed to normalize URL {url}: {e}")
        return url


def is_aggregator(url: str) -> bool:
    """Check if a URL belongs to an aggregator, news, or social media domain.
    Handles TLD patterns (e.g. '.edu') when the entry starts with '.'.
    """
    try:
        domain = urlparse(url).netloc.lower()
        for agg in AGGREGATOR_DOMAINS:
            if agg.startswith("."):
                if domain.endswith(agg):
                    return True
            elif domain == agg or domain.endswith("." + agg):
                return True
        return False
    except Exception as e:
        logging.warning(f"Failed to check if URL {url} is aggregator: {e}")
        return True


def get_search_queries() -> List[str]:
    """Generate date-filtered search queries for finding AI tools from the last 7 days."""
    last_7_days = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    return [f"{q} after:{last_7_days}" for q in BASE_QUERIES]


async def search_web_for_ai_tools_serper(query: str, num_results: int = 38) -> List[str]:
    """Search for AI tools using the Serper.dev API."""
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    params = {"q": query, "gl": "us", "hl": "en", "num": num_results}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params, headers=headers) as resp:
                if resp.status != 200:
                    logging.error(f"Serper API error: {resp.status} - {await resp.text()}")
                    return []
                data = await resp.json()
                urls = [r["link"] for r in data.get("organic", []) if "link" in r]
                logging.info(f"Serper query '{query[:50]}...' returned {len(urls)} results")
                return urls
    except Exception as e:
        logging.error(f"Serper search failed for query '{query[:50]}...': {e}")
        return []


async def search_web_for_ai_tools_serpapi(query: str, num_results: int = 38) -> List[str]:
    """Search for AI tools using the SerpAPI."""
    try:
        from serpapi import GoogleSearch

        params = {
            "q": query,
            "api_key": SERPAPI_API_KEY,
            "num": num_results,
            "hl": "en",
            "gl": "us",
            "engine": "google",
        }

        loop = asyncio.get_running_loop()
        search = GoogleSearch(params)
        results = await loop.run_in_executor(None, search.get_dict)

        urls = [r["link"] for r in results.get("organic_results", []) if "link" in r]
        logging.info(f"SerpAPI query '{query[:50]}...' returned {len(urls)} results")
        return urls
    except Exception as e:
        logging.error(f"SerpAPI search failed for query '{query[:50]}...': {e}")
        return []


async def _run_engine(search_fn, queries: List[str]) -> list:
    """Run all queries against a single search engine in batches."""
    results = []
    for i in range(0, len(queries), BATCH_SIZE):
        batch = queries[i : i + BATCH_SIZE]
        batch_results = await asyncio.gather(
            *(search_fn(query, num_results=38) for query in batch),
            return_exceptions=True,
        )
        results.extend(batch_results)
        if i + BATCH_SIZE < len(queries):
            await asyncio.sleep(1)
    return results


async def run_search() -> List[str]:
    """Run search across Serper and SerpAPI, returning unique non-aggregator URLs."""
    queries = get_search_queries()
    logging.info(f"Starting search with {len(queries)} queries")

    serper_results, serpapi_results = await asyncio.gather(
        _run_engine(search_web_for_ai_tools_serper, queries),
        _run_engine(search_web_for_ai_tools_serpapi, queries),
    )

    urls: Set[str] = set()
    for api_results in [serper_results, serpapi_results]:
        for i, result in enumerate(api_results):
            if isinstance(result, Exception):
                logging.error(f"Search query {i} failed: {result}")
                continue
            for url in result:
                if not is_aggregator(url):
                    urls.add(normalize_url(url))

    logging.info(f"Found {len(urls)} unique non-aggregator URLs")
    return list(urls)

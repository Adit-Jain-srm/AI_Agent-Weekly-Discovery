"""
search_agent.py: Handles all search engine logic, query construction, and aggregator/news filtering.
- This module does not use ToolInfo, LLM prompts, or LLM input truncation constants directly.
"""
from typing import List, Set
from datetime import datetime, timedelta, timezone
import asyncio
import aiohttp
from urllib.parse import urlparse, urlunparse
import logging
from agents.config_agent import SERPER_API_KEY, SERPAPI_API_KEY
from config.constants import AGGREGATOR_DOMAINS, BATCH_SIZE, BASE_QUERIES


def normalize_url(url: str) -> str:
    """
    Normalize URL by removing query parameters and fragments for better deduplication.
    
    Args:
        url: The URL to normalize
        
    Returns:
        Normalized URL with query parameters and fragments removed
    """
    try:
        parsed = urlparse(url)
        # Remove query parameters and fragments, keep scheme, netloc, and path
        normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
        return normalized
    except Exception as e:
        logging.warning(f"Failed to normalize URL {url}: {e}")
        return url

def is_aggregator(url: str) -> bool:
    """
    Check if a URL belongs to an aggregator, news, or social media domain.
    Handles TLDs (e.g. '.edu') if agg starts with '.', else matches exact or subdomain.
    """
    try:
        domain = urlparse(url).netloc.lower()
        for agg in AGGREGATOR_DOMAINS:
            if agg.startswith('.'):
                if domain.endswith(agg):
                    return True
            elif domain == agg or domain.endswith('.' + agg):
                return True
        return False
    except Exception as e:
        logging.warning(f"Failed to check if URL {url} is aggregator: {e}")
        return True  # Default to filtering out if we can't parse

def get_search_queries() -> List[str]:
    """
    Generate a small set of broad search queries for finding new AI tools, products, and launches from the last 7 days.
    Returns:
        List of search query strings optimized for finding new AI tool launches
    """
    last_7_days = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%d')
    # Use BASE_QUERIES from config/constants.py
    queries = [f"{q} after:{last_7_days}" for q in BASE_QUERIES]
    return queries

async def search_web_for_ai_tools_serper(query: str, num_results: int = 38) -> List[str]:
    """
    Search for AI tools using Serper.dev API asynchronously.
    
    Args:
        query: Search query string
        num_results: Number of results to return (default: 38)
        
    Returns:
        List of URLs from search results
    """
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    params = {
        "q": query,
        "gl": "us",
        "hl": "en",
        "num": num_results
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params, headers=headers) as resp:
                if resp.status != 200:
                    logging.error(f"Serper API error: {resp.status} - {await resp.text()}")
                    return []
                
                data = await resp.json()
                results = data.get("organic", [])
                urls = [r["link"] for r in results if "link" in r]
                logging.info(f"Serper query '{query[:50]}...' returned {len(urls)} results")
                return urls
    except Exception as e:
        logging.error(f"Serper search failed for query '{query[:50]}...': {e}")
        return []

async def search_web_for_ai_tools_serpapi(query: str, num_results: int = 38) -> List[str]:
    """
    Search for AI tools using SerpAPI asynchronously.
    
    Args:
        query: Search query string
        num_results: Number of results to return (default: 38)
        
    Returns:
        List of URLs from search results
    """
    try:
        # Import here to avoid blocking the event loop during import
        from serpapi import GoogleSearch
        
        params = {
            "q": query,
            "api_key": SERPAPI_API_KEY,
            "num": num_results,
            "hl": "en",
            "gl": "us",
            "engine": "google"
        }
        
        # Run SerpAPI in a thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        search = GoogleSearch(params)
        results = await loop.run_in_executor(None, search.get_dict)
        
        organic = results.get("organic_results", [])
        urls = [r["link"] for r in organic if "link" in r]
        logging.info(f"SerpAPI query '{query[:50]}...' returned {len(urls)} results")
        return urls
    except Exception as e:
        logging.error(f"SerpAPI search failed for query '{query[:50]}...': {e}")
        return []

async def run_search() -> List[str]:
    """
    Run search across multiple engines and queries to find AI tool URLs.
    Returns:
        List of unique, normalized URLs for AI tools
    """
    queries = get_search_queries()
    urls: Set[str] = set()
    logging.info(f"Starting search with {len(queries)} queries")

    # Serper
    async def run_serper():
        results = []
        for i in range(0, len(queries), BATCH_SIZE):
            batch = queries[i:i+BATCH_SIZE]
            logging.debug(f"Serper batch {i//BATCH_SIZE+1}: queries {i+1}-{min(i+BATCH_SIZE, len(queries))}")
            batch_results = await asyncio.gather(
                *(search_web_for_ai_tools_serper(query, num_results=38) for query in batch),
                return_exceptions=True
            )
            results.extend(batch_results)
            if i + BATCH_SIZE < len(queries):
                await asyncio.sleep(1)
        return results
    # SerpApi
    async def run_serpapi():
        results = []
        for i in range(0, len(queries), BATCH_SIZE):
            batch = queries[i:i+BATCH_SIZE]
            logging.debug(f"SerpApi batch {i//BATCH_SIZE+1}: queries {i+1}-{min(i+BATCH_SIZE, len(queries))}")
            batch_results = await asyncio.gather(
                *(search_web_for_ai_tools_serpapi(query, num_results=38) for query in batch),
                return_exceptions=True
            )
            results.extend(batch_results)
            if i + BATCH_SIZE < len(queries):
                await asyncio.sleep(1)
        return results
    # Run both APIs in parallel
    serper_results, serpapi_results = await asyncio.gather(run_serper(), run_serpapi())
    # Merge and process results
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
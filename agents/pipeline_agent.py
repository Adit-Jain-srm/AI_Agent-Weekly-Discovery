"""
pipeline_agent.py: Orchestrates the workflow from search to LLM-based extraction, deduplication, and output.
- Uses only LLM-based extraction (GPT-4o) for all tool info fields in a single call per tool, with ToolInfo from models.tool_info and prompts from prompts/ loaded via utils/prompt_loader.
- LLM input truncation limit is set in config/constants.py.
"""
import asyncio
import aiohttp
from typing import Optional, AsyncGenerator
from openai import RateLimitError
from models.tool_info import ToolInfo
from config.constants import BATCH_SIZE, LLM_CONCURRENCY_LIMIT
from agents.search_agent import run_search
from agents.scraper_agent import fetch_with_retries, extract_tool_info_with_llm, is_allowed_by_robots, _html_fetch_cache, DEFAULT_HEADERS
import logging
from utils.error_handling import ScrapingError
import time
from tqdm import tqdm
from utils.blacklist import PersistentBlacklist

_llm_semaphore = asyncio.Semaphore(LLM_CONCURRENCY_LIMIT)

class PipelineContext:
    """
    Async context manager for pipeline resources (e.g., shared aiohttp session).
    """
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

async def extract_tool_info_with_llm_throttled(html, url):
    async with _llm_semaphore:
        return await extract_tool_info_with_llm(html, url)

async def extract_tool_info_with_llm_throttled_with_retry(html, url, retries=3, delay=10):
    for attempt in range(retries):
        try:
            return await extract_tool_info_with_llm_throttled(html, url)
        except RateLimitError:
            if attempt < retries - 1:
                await asyncio.sleep(delay)
            else:
                raise

async def fetch_with_retries(url: str, session: aiohttp.ClientSession, retries: int = 3, timeout: int = 30) -> str:
    """Fetch HTML from a URL with retries and exponential backoff for transient errors (503, timeouts)."""
    delay = 2
    for attempt in range(retries):
        try:
            # ... robots.txt and header logic ...
            allowed = await is_allowed_by_robots(url)
            if not allowed:
                logging.warning(f"robots.txt disallows scraping {url}. Skipping fetch.")
                _html_fetch_cache[url] = ""
                return ""
            headers = DEFAULT_HEADERS
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), ssl=False, headers=headers) as resp:
                if resp.status == 200:
                    html = await resp.text(encoding=resp.charset or "utf-8", errors="replace")
                    _html_fetch_cache[url] = html if html is not None else ""
                    return _html_fetch_cache[url]
                elif resp.status == 503 and attempt < retries - 1:
                    logging.warning(f"HTTP 503 for {url}, retrying after {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                else:
                    logging.warning(f"HTTP {resp.status} for {url}")
                    _html_fetch_cache[url] = ""
                    raise ScrapingError(f"HTTP {resp.status} for {url}", context={"url": url, "step": "fetch_with_retries", "status": resp.status})
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt < retries - 1:
                logging.warning(f"Connection error for {url}: {e}, retrying after {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2
                continue
            logging.warning(f"Connection error for {url}: {e}")
            _html_fetch_cache[url] = ""
            raise ScrapingError(f"Connection error for {url}: {e}", context={"url": url, "step": "fetch_with_retries", "error": str(e)})
        except Exception as e:
            logging.error(f"Unexpected error for {url}: {e}")
            _html_fetch_cache[url] = ""
            raise ScrapingError(f"Unexpected error for {url}: {e}", context={"url": url, "step": "fetch_with_retries", "error": str(e)})
    return ""

async def fetch_all_html(urls, session):
    html_map = {}
    error_list = []
    for i in tqdm(range(0, len(urls), BATCH_SIZE), desc="Fetching HTML", unit="batch"):
        batch = urls[i:i+BATCH_SIZE]
        tasks = [fetch_with_retries(url, session) for url in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for url, result in zip(batch, results):
            if isinstance(result, Exception):
                # Log error with context if available
                if hasattr(result, 'context'):
                    logging.error(f"Error fetching {url}: {result} | Context: {getattr(result, 'context', {})}")
                    error_list.append({"url": url, "error": str(result), "context": getattr(result, 'context', {})})
                else:
                    logging.error(f"Error fetching {url}: {result}")
                    error_list.append({"url": url, "error": str(result)})
                html_map[url] = ""
            else:
                html_map[url] = result
    return html_map, error_list

async def run_pipeline():
    async with PipelineContext() as ctx:
        # 1. Search for tool URLs
        urls = await run_search()
        if not urls:
            return []
        # 2. Fetch HTML for all URLs (async, batched)
        html_map, error_list = await fetch_all_html(urls, ctx.session)
        # 3. Extract tool info from HTML using LLM (single call per tool, async, throttled, with retry)
        async def extract_all_tool_info(html_map):
            results = []
            urls_and_htmls = [(url, html) for url, html in html_map.items() if html]
            for i in tqdm(range(len(urls_and_htmls)), desc="LLM Extraction", unit="tool"):
                url, html = urls_and_htmls[i]
                result = await extract_tool_info_with_llm_throttled_with_retry(html, url)
                results.append(result)
                import logging
                logging.info(f"LLM result received for {url}")
            return results
        tools = await extract_all_tool_info(html_map)
        tools = [tool for tool in tools if getattr(tool, 'ai_tool_annotation', None) == 'ai_tool']
        # --- Merge Product Hunt AI tools (async) ---
        # Product Hunt integration removed
        # Deduplicate by website or title
        seen = set()
        deduped_tools = []
        for t in tools:
            key = (getattr(t, 'website', '').lower(), getattr(t, 'title', '').lower())
            if key in seen:
                continue
            seen.add(key)
            deduped_tools.append(t)
        # Only return tools classified as AI tools (already filtered above for LLM-extracted tools)
        # --- Post-process: filter out results older than 7 days based on publish_date (if available) ---
        from datetime import datetime, timezone, timedelta
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        filtered_tools = []
        for tool in deduped_tools:
            date_str = getattr(tool, 'publish_date', None)
            if date_str:
                try:
                    # Accept only YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ formats
                    if 'T' in date_str:
                        pub_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        pub_date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    if pub_date >= seven_days_ago:
                        filtered_tools.append(tool)
                except Exception:
                    # If date parsing fails, keep the tool (conservative)
                    filtered_tools.append(tool)
            else:
                filtered_tools.append(tool)
        # Print error summary
        if error_list:
            print("\n=== Error Summary ===")
            for err in error_list:
                print(f"URL: {err['url']}")
                print(f"Error: {err['error']}")
                if 'context' in err:
                    print(f"Context: {err['context']}")
                print('-' * 40)
        # Print summary report
        num_success = sum(1 for html in html_map.values() if html)
        num_fail = len(error_list)
        num_total = len(html_map)
        print(f"\n=== Summary Report ===")
        print(f"Total URLs processed: {num_total}")
        print(f"Successful fetches: {num_success}")
        print(f"Failed fetches: {num_fail}")
        print(f"Skipped (robots.txt or empty): {num_total - num_success - num_fail}")
        # Save persistent blacklist and print new blacklisted domains
        from agents.scraper_agent import blacklist
        blacklist.save()
        new_blacklisted = blacklist.summary()
        if new_blacklisted:
            print(f"\n=== Blacklisted Domains (Persistent) ===")
            for domain in new_blacklisted:
                print(f"Blacklisted: {domain}")
        return filtered_tools 

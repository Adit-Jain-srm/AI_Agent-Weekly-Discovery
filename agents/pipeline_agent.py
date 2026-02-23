"""
pipeline_agent.py: Orchestrates the workflow from search to LLM-based extraction, deduplication, and output.
- Uses only LLM-based extraction (GPT-4o) for all tool info fields in a single call per tool,
  with ToolInfo from models.tool_info and prompts from prompts/ loaded via utils/prompt_loader.
- LLM input truncation limit is set in config/constants.py.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

import aiohttp
from openai import RateLimitError
from tqdm import tqdm

from models.tool_info import ToolInfo
from config.constants import BATCH_SIZE, LLM_CONCURRENCY_LIMIT
from agents.search_agent import run_search
from agents.scraper_agent import (
    fetch_with_retries,
    extract_tool_info_with_llm,
    blacklist,
)
_llm_semaphore = asyncio.Semaphore(LLM_CONCURRENCY_LIMIT)


class PipelineContext:
    """Async context manager for pipeline resources (shared aiohttp session)."""

    def __init__(self) -> None:
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "PipelineContext":
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.session:
            await self.session.close()


async def _extract_throttled(html: str, url: str) -> ToolInfo:
    """Run LLM extraction with concurrency throttling."""
    async with _llm_semaphore:
        return await extract_tool_info_with_llm(html, url)


async def _extract_with_retry(html: str, url: str, retries: int = 3, delay: float = 10) -> ToolInfo:
    """Run throttled LLM extraction with retry on rate-limit errors."""
    for attempt in range(retries):
        try:
            return await _extract_throttled(html, url)
        except RateLimitError:
            if attempt < retries - 1:
                logging.warning(f"Rate limited for {url}, retrying in {delay}s (attempt {attempt + 1}/{retries})")
                await asyncio.sleep(delay)
            else:
                raise
    return ToolInfo(title="", website=url, summary="", source=url, ai_tool_annotation="not_ai_tool")


async def fetch_all_html(
    urls: list[str], session: aiohttp.ClientSession
) -> tuple[dict[str, str], list[dict]]:
    """Fetch HTML for all URLs in batches with progress reporting."""
    html_map: dict[str, str] = {}
    error_list: list[dict] = []

    for i in tqdm(range(0, len(urls), BATCH_SIZE), desc="Fetching HTML", unit="batch"):
        batch = urls[i : i + BATCH_SIZE]
        tasks = [fetch_with_retries(url, session) for url in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for url, result in zip(batch, results):
            if isinstance(result, Exception):
                context = getattr(result, "context", {})
                logging.error(f"Error fetching {url}: {result} | Context: {context}")
                error_list.append({"url": url, "error": str(result), "context": context})
                html_map[url] = ""
            else:
                html_map[url] = result

    return html_map, error_list


async def extract_all_tool_info(html_map: dict[str, str]) -> list[ToolInfo]:
    """Extract tool info from all fetched HTML pages using parallel throttled LLM calls."""
    urls_and_htmls = [(url, html) for url, html in html_map.items() if html]
    if not urls_and_htmls:
        return []

    tasks = [_extract_with_retry(html, url) for url, html in urls_and_htmls]

    results: list[ToolInfo] = []
    with tqdm(total=len(tasks), desc="LLM Extraction", unit="tool") as pbar:
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            pbar.update(1)

    return results


def _deduplicate(tools: list[ToolInfo]) -> list[ToolInfo]:
    """Deduplicate tools by (website, title) pair."""
    seen: set[tuple[str, str]] = set()
    deduped: list[ToolInfo] = []
    for t in tools:
        key = (t.website.lower(), t.title.lower())
        if key not in seen:
            seen.add(key)
            deduped.append(t)
    return deduped


def _filter_by_recency(tools: list[ToolInfo], days: int = 7) -> list[ToolInfo]:
    """Keep only tools published within the last N days (or with unparseable/missing dates)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    filtered: list[ToolInfo] = []

    for tool in tools:
        if not tool.publish_date:
            filtered.append(tool)
            continue
        try:
            if "T" in tool.publish_date:
                pub_date = datetime.fromisoformat(tool.publish_date.replace("Z", "+00:00"))
            else:
                pub_date = datetime.strptime(tool.publish_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

            if pub_date >= cutoff:
                filtered.append(tool)
        except (ValueError, TypeError):
            filtered.append(tool)

    return filtered


def _print_summary_report(
    html_map: dict[str, str], error_list: list[dict]
) -> None:
    """Print error summary and fetch statistics."""
    if error_list:
        print("\n=== Error Summary ===")
        for err in error_list:
            print(f"URL: {err['url']}")
            print(f"Error: {err['error']}")
            if err.get("context"):
                print(f"Context: {err['context']}")
            print("-" * 40)

    num_total = len(html_map)
    num_success = sum(1 for html in html_map.values() if html)
    num_fail = len(error_list)

    print(f"\n=== Summary Report ===")
    print(f"Total URLs processed: {num_total}")
    print(f"Successful fetches:   {num_success}")
    print(f"Failed fetches:       {num_fail}")
    print(f"Skipped (robots/empty): {num_total - num_success - num_fail}")


async def run_pipeline() -> list[ToolInfo]:
    """Execute the full discovery pipeline: search -> fetch -> extract -> filter -> output."""
    async with PipelineContext() as ctx:
        urls = await run_search()
        if not urls:
            logging.info("No URLs found during search phase.")
            return []

        html_map, error_list = await fetch_all_html(urls, ctx.session)

        tools = await extract_all_tool_info(html_map)

        ai_tools = [t for t in tools if t.ai_tool_annotation == "ai_tool"]
        ai_tools = _deduplicate(ai_tools)
        ai_tools = _filter_by_recency(ai_tools)

        _print_summary_report(html_map, error_list)

        blacklist.save()
        blacklisted_domains = blacklist.summary()
        if blacklisted_domains:
            print("\n=== Blacklisted Domains (Persistent) ===")
            for domain in blacklisted_domains:
                print(f"  {domain}")

        return ai_tools

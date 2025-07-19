"""
scraper_agent.py: Async HTML fetching and 100% LLM-based tool info extraction, summarization, and classification using GPT-4o (Azure OpenAI).
- Uses ToolInfo dataclass from models.tool_info, async HTML fetch, and extract_tool_info_with_llm().
- All extraction, summarization, and classification is performed in a single LLM call per tool using prompts from prompts/ loaded via utils/prompt_loader.
- LLM input truncation limit is set in config/constants.py.
"""
from typing import Dict, Optional, List, Any
import aiohttp
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json
from openai import AsyncAzureOpenAI
from agents.config_agent import AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT
import re
from models.tool_info import ToolInfo
from utils.prompt_loader import load_prompt, is_allowed_by_robots
from config.constants import LLM_INPUT_TRUNCATION_LIMIT, DEFAULT_HEADERS, NON_RETRYABLE_STATUS_CODES
from utils.error_handling import ScrapingError, ExtractionError
from urllib.parse import urlparse
from utils.blacklist import PersistentBlacklist

# Asyncio cache for HTML fetches (per run)
_html_fetch_cache = {}

blacklist = PersistentBlacklist()

async def fetch_with_retries(url: str, session: aiohttp.ClientSession, retries: int = 3, timeout: int = 30) -> str:
    """Fetch HTML from a URL with retries and exponential backoff for transient errors (503, timeouts). Skips blacklisted domains and retry on non-retryable status codes."""
    parsed = urlparse(url)
    if blacklist.is_blacklisted(parsed.netloc):
        logging.warning(f"Domain {parsed.netloc} is blacklisted. Skipping fetch for {url}.")
        _html_fetch_cache[url] = ""
        return ""
    delay = 2
    for attempt in range(retries):
        try:
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
                elif resp.status in NON_RETRYABLE_STATUS_CODES:
                    _html_fetch_cache[url] = ""
                    blacklist.record_failure(parsed.netloc)
                    raise ScrapingError(f"HTTP {resp.status} for {url}", context={"url": url, "step": "fetch_with_retries", "status": resp.status})
                else:
                    _html_fetch_cache[url] = ""
                    if attempt < retries - 1:
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                    blacklist.record_failure(parsed.netloc)
                    raise ScrapingError(f"HTTP {resp.status} for {url}", context={"url": url, "step": "fetch_with_retries", "status": resp.status})
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt < retries - 1:
                logging.warning(f"Connection error for {url}: {e}, retrying after {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2
                continue
            _html_fetch_cache[url] = ""
            blacklist.record_failure(parsed.netloc)
            raise ScrapingError(f"Connection error for {url}: {e}", context={"url": url, "step": "fetch_with_retries", "error": str(e)})
        except Exception as e:
            _html_fetch_cache[url] = ""
            blacklist.record_failure(parsed.netloc)
            raise ScrapingError(f"Unexpected error for {url}: {e}", context={"url": url, "step": "fetch_with_retries", "error": str(e)})
    return ""

async def fetch_html_batch(urls: List[str]) -> Dict[str, str]:
    """Fetch HTML for a batch of URLs asynchronously, reusing a single session and using a cache for duplicates."""
    results = {}
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_with_retries(url, session) for url in urls]
        responses = await asyncio.gather(*tasks)
        for url, html in zip(urls, responses):
            results[url] = html
    return results

# LLM client setup
if not AZURE_OPENAI_ENDPOINT:
    raise ValueError("AZURE_OPENAI_ENDPOINT is not set in environment variables.")

client = AsyncAzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version="2025-01-01-preview",
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)

deployment = AZURE_OPENAI_DEPLOYMENT or "gpt-4o"
if not AZURE_OPENAI_DEPLOYMENT:
    logging.warning("AZURE_OPENAI_DEPLOYMENT not set, defaulting to 'gpt-4o'")

async def extract_tool_info_with_llm(html: str, url: str) -> ToolInfo:
    """
    Use GPT-4o to extract all relevant tool info fields from raw HTML and URL in a single call.
    Returns ToolInfo with ai_tool_annotation set to 'ai_tool' or 'not_ai_tool'.
    If an error occurs, the error message is included in the summary field for diagnostics.
    """
    html_trunc = html[:LLM_INPUT_TRUNCATION_LIMIT] if html else ""
    if html and len(html) > LLM_INPUT_TRUNCATION_LIMIT:
        logging.warning(f"HTML for {url} truncated to {LLM_INPUT_TRUNCATION_LIMIT} characters for LLM prompt.")
    # --- ADVANCED LLM EXTRACTION PROMPT ENGINEERING ---
    system_prompt = load_prompt("system_prompt.txt")
    user_prompt_template = load_prompt("user_prompt.txt")
    user_prompt = user_prompt_template.format(url=url, html_trunc=html_trunc)
    try:
        response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=800,
            temperature=0.4,
        )
        llm_content = response.choices[0].message.content
        if llm_content:
            llm_content = llm_content.strip()
            if llm_content.startswith('```'):
                llm_content = re.sub(r'^```(?:json)?|```$', '', llm_content, flags=re.MULTILINE).strip()
            match = re.search(r'\{.*\}', llm_content, re.DOTALL)
            if match:
                llm_content = match.group(0)
        if llm_content and llm_content.startswith('{'):
            data = json.loads(llm_content)
            website = data.get('Website') or url
            source = data.get('Source URL') or url
            logging.info(f"LLM result: Title='{data.get('Title', '')}', Website='{website}', ai_tool_annotation='{data.get('ai_tool_annotation', '')}'")
            return ToolInfo(
                title=data.get('Title', ''),
                website=website,
                summary=data.get('Core Functionality', '') or data.get('Summary', ''),
                features=data.get('Key Features', []),
                pricing=data.get('Pricing', None),
                source=source,
                target_audience=data.get('Target Audience', None),
                main_text=html_trunc,
                ai_tool_annotation=data.get('ai_tool_annotation', 'not_ai_tool'),
                tags=data.get('Tags', []),
                publish_date=data.get('Publish Date', None),  # Try to extract publish date if present
            )
        else:
            logging.warning(f"LLM extraction returned non-JSON content: {llm_content}")
    except Exception as e:
        logging.error(f"LLM extraction failed: {e!r}", exc_info=True)
        raise ExtractionError(f"LLM extraction failed for {url}: {e}", context={"url": url, "step": "extract_tool_info_with_llm", "error": str(e)})
    # Fallback: minimal ToolInfo
    return ToolInfo(
        title="",
        website=url,
        summary="",
        features=[],
        pricing=None,
        source=url,
        target_audience=None,
        main_text=html_trunc,
        ai_tool_annotation='not_ai_tool',
        tags=[],
        publish_date=None,
    )
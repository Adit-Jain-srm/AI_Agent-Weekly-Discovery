"""
scraper_agent.py: Async HTML fetching and LLM-based tool info extraction using GPT-4o (Azure OpenAI).
- Uses ToolInfo dataclass from models.tool_info.
- All extraction, summarization, and classification is performed in a single LLM call per tool
  using prompts from prompts/ loaded via utils/prompt_loader.
- LLM input truncation limit is set in config/constants.py.
"""
import asyncio
import json
import logging
import re
from typing import Optional
from urllib.parse import urlparse

import aiohttp
from openai import AsyncAzureOpenAI

from agents.config_agent import AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT
from config.constants import LLM_INPUT_TRUNCATION_LIMIT, DEFAULT_HEADERS, NON_RETRYABLE_STATUS_CODES
from models.tool_info import ToolInfo
from utils.blacklist import PersistentBlacklist
from utils.error_handling import ScrapingError, ExtractionError
from utils.prompt_loader import load_prompt, is_allowed_by_robots

_html_fetch_cache: dict[str, str] = {}

blacklist = PersistentBlacklist()

_client: Optional[AsyncAzureOpenAI] = None
_deployment: str = ""

_system_prompt: Optional[str] = None
_user_prompt_template: Optional[str] = None


def _get_client() -> AsyncAzureOpenAI:
    """Lazy-initialize the Azure OpenAI client on first use."""
    global _client, _deployment
    if _client is None:
        if not AZURE_OPENAI_ENDPOINT:
            raise ValueError("AZURE_OPENAI_ENDPOINT is not set in environment variables.")
        _client = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version="2025-01-01-preview",
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
        )
        _deployment = AZURE_OPENAI_DEPLOYMENT or "gpt-4o"
        if not AZURE_OPENAI_DEPLOYMENT:
            logging.warning("AZURE_OPENAI_DEPLOYMENT not set, defaulting to 'gpt-4o'")
    return _client


def _get_prompts() -> tuple[str, str]:
    """Load and cache prompt templates from disk (loaded once per process)."""
    global _system_prompt, _user_prompt_template
    if _system_prompt is None:
        _system_prompt = load_prompt("system_prompt.txt")
        _user_prompt_template = load_prompt("user_prompt.txt")
    return _system_prompt, _user_prompt_template


async def fetch_with_retries(
    url: str, session: aiohttp.ClientSession, retries: int = 3, timeout: int = 30
) -> str:
    """Fetch HTML from a URL with retries and exponential backoff.
    Skips blacklisted domains and non-retryable status codes.
    """
    parsed = urlparse(url)
    domain = parsed.netloc

    if blacklist.is_blacklisted(domain):
        logging.warning(f"Domain {domain} is blacklisted. Skipping fetch for {url}.")
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

            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                ssl=False,
                headers=DEFAULT_HEADERS,
            ) as resp:
                if resp.status == 200:
                    html = await resp.text(encoding=resp.charset or "utf-8", errors="replace")
                    _html_fetch_cache[url] = html or ""
                    return _html_fetch_cache[url]

                if resp.status in NON_RETRYABLE_STATUS_CODES:
                    _html_fetch_cache[url] = ""
                    blacklist.record_failure(domain)
                    raise ScrapingError(
                        f"HTTP {resp.status} for {url}",
                        context={"url": url, "step": "fetch_with_retries", "status": resp.status},
                    )

                if attempt < retries - 1:
                    logging.warning(f"HTTP {resp.status} for {url}, retrying after {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue

                _html_fetch_cache[url] = ""
                blacklist.record_failure(domain)
                raise ScrapingError(
                    f"HTTP {resp.status} for {url}",
                    context={"url": url, "step": "fetch_with_retries", "status": resp.status},
                )

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt < retries - 1:
                logging.warning(f"Connection error for {url}: {e}, retrying after {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2
                continue
            _html_fetch_cache[url] = ""
            blacklist.record_failure(domain)
            raise ScrapingError(
                f"Connection error for {url}: {e}",
                context={"url": url, "step": "fetch_with_retries", "error": str(e)},
            )
        except ScrapingError:
            raise
        except Exception as e:
            _html_fetch_cache[url] = ""
            blacklist.record_failure(domain)
            raise ScrapingError(
                f"Unexpected error for {url}: {e}",
                context={"url": url, "step": "fetch_with_retries", "error": str(e)},
            )

    return ""


def _parse_llm_json(raw: str | None) -> dict | None:
    """Extract and parse JSON from an LLM response that may contain markdown fences."""
    if not raw:
        return None

    content = raw.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()

    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    return None


async def extract_tool_info_with_llm(html: str, url: str) -> ToolInfo:
    """
    Use GPT-4o to extract all relevant tool info fields from raw HTML and URL in a single call.
    Returns a ToolInfo with ai_tool_annotation set to 'ai_tool' or 'not_ai_tool'.
    """
    client = _get_client()
    system_prompt, user_prompt_template = _get_prompts()

    html_trunc = html[:LLM_INPUT_TRUNCATION_LIMIT] if html else ""
    if html and len(html) > LLM_INPUT_TRUNCATION_LIMIT:
        logging.warning(f"HTML for {url} truncated to {LLM_INPUT_TRUNCATION_LIMIT} chars for LLM prompt.")

    user_prompt = user_prompt_template.format(url=url, html_trunc=html_trunc)

    try:
        response = await client.chat.completions.create(
            model=_deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=800,
            temperature=0.4,
        )

        data = _parse_llm_json(response.choices[0].message.content)
        if data:
            website = data.get("Website") or url
            source = data.get("Source URL") or url
            logging.info(
                f"LLM result: Title='{data.get('Title', '')}', "
                f"Website='{website}', ai_tool_annotation='{data.get('ai_tool_annotation', '')}'"
            )
            return ToolInfo(
                title=data.get("Title", ""),
                website=website,
                summary=data.get("Core Functionality", "") or data.get("Summary", ""),
                features=data.get("Key Features", []),
                pricing=data.get("Pricing") or None,
                source=source,
                target_audience=data.get("Target Audience") or None,
                main_text=html_trunc,
                ai_tool_annotation=data.get("ai_tool_annotation", "not_ai_tool"),
                tags=data.get("Tags", []),
                publish_date=data.get("Publish Date") or None,
            )

        logging.warning(f"LLM extraction returned non-JSON for {url}")

    except ExtractionError:
        raise
    except Exception as e:
        logging.error(f"LLM extraction failed for {url}: {e!r}", exc_info=True)
        raise ExtractionError(
            f"LLM extraction failed for {url}: {e}",
            context={"url": url, "step": "extract_tool_info_with_llm", "error": str(e)},
        )

    return ToolInfo(
        title="",
        website=url,
        summary="",
        features=[],
        source=url,
        main_text=html_trunc,
        ai_tool_annotation="not_ai_tool",
        tags=[],
    )

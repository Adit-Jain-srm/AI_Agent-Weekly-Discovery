import logging
import os
from typing import Dict
from urllib.parse import urlparse

import aiohttp

_robots_cache: Dict[str, str] = {}
_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


def load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts directory.

    Args:
        filename: Name of the prompt file (e.g. 'system_prompt.txt').

    Returns:
        Contents of the prompt file.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    path = os.path.join(_PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


async def is_allowed_by_robots(url: str, user_agent: str = "Mozilla/5.0") -> bool:
    """Check robots.txt to determine if fetching the URL is permitted.
    Results are cached per domain for efficiency.
    Returns True when in doubt (missing/malformed robots.txt or errors).
    """
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            logging.warning(f"Invalid URL for robots.txt check: {url}")
            return True
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    except Exception as e:
        logging.warning(f"Exception parsing URL for robots.txt: {url} | {e}")
        return True

    if robots_url in _robots_cache:
        content = _robots_cache[robots_url]
    else:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return True
                    content = await resp.text()
                    _robots_cache[robots_url] = content
        except Exception as e:
            logging.warning(f"Error fetching robots.txt for {robots_url}: {e}")
            return True

    try:
        allowed = True
        current_ua = None
        for line in content.splitlines():
            line = line.strip()
            if line.lower().startswith("user-agent:"):
                current_ua = line.split(":", 1)[1].strip()
            elif line.lower().startswith("disallow:") and (
                current_ua == "*" or (current_ua is not None and user_agent in current_ua)
            ):
                path = line.split(":", 1)[1].strip()
                if path and parsed.path.startswith(path):
                    allowed = False
        return allowed
    except Exception as e:
        logging.warning(f"Malformed robots.txt for {robots_url}: {e}")
        return True

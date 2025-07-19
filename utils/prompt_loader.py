import os
from urllib.parse import urlparse
import aiohttp
from typing import Dict
import logging

_robots_cache: Dict[str, str] = {}

def load_prompt(filename: str) -> str:
    """
    Load a prompt template from the prompts directory.
    Args:
        filename (str): The name of the prompt file (e.g., 'system_prompt.txt').
    Returns:
        str: The contents of the prompt file as a string.
    Raises:
        FileNotFoundError: If the file does not exist.
    """
    prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts')
    path = os.path.join(prompts_dir, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

async def is_allowed_by_robots(url: str, user_agent: str = "Mozilla/5.0") -> bool:
    """
    Check robots.txt to see if the given user-agent is allowed to fetch the URL.
    Returns True if allowed, False if disallowed, True if robots.txt is missing, malformed, or on error (including invalid URLs).
    Uses a simple in-memory cache per domain for efficiency.
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
    # Check cache first
    if robots_url in _robots_cache:
        content = _robots_cache[robots_url]
    else:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return True  # No robots.txt, assume allowed
                    content = await resp.text()
                    _robots_cache[robots_url] = content
        except Exception as e:
            logging.warning(f"Error fetching robots.txt for {robots_url}: {e}")
            return True  # On error, assume allowed
    try:
        lines = content.splitlines()
        allowed = True
        ua = None
        for line in lines:
            line = line.strip()
            if line.lower().startswith("user-agent:"):
                ua = line.split(":", 1)[1].strip()
            elif line.lower().startswith("disallow:") and (ua == "*" or (ua is not None and user_agent in ua)):
                path = line.split(":", 1)[1].strip()
                if path and parsed.path.startswith(path):
                    allowed = False
        return allowed
    except Exception as e:
        logging.warning(f"Malformed robots.txt for {robots_url}: {e}")
        return True  # On parse error, assume allowed 
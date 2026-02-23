"""
config_agent.py: Handles environment variable loading, API key setup, and logging configuration.
"""
import logging
import os
from typing import Optional

import dotenv

dotenv.load_dotenv()

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT: Optional[str] = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY: Optional[str] = os.environ.get("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT: Optional[str] = os.environ.get("AZURE_OPENAI_DEPLOYMENT")

# Search API Configuration
SERPER_API_KEY: Optional[str] = os.environ.get("SERPER_API_KEY")
SERPAPI_API_KEY: Optional[str] = os.environ.get("SERPAPI_API_KEY")


def setup_logging() -> None:
    """Configure logging with timestamp formatting and reduced noise from third-party libraries."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for lib in ("aiohttp", "openai", "azure", "urllib3"):
        logging.getLogger(lib).setLevel(logging.WARNING)


def validate_critical_config() -> None:
    """Validate that all critical API keys are present.

    Raises:
        ValueError: If any critical configuration is missing.
    """
    required = {
        "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
        "AZURE_OPENAI_KEY": AZURE_OPENAI_KEY,
        "SERPER_API_KEY": SERPER_API_KEY,
        "SERPAPI_API_KEY": SERPAPI_API_KEY,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(
            f"Missing critical configuration: {', '.join(missing)}. "
            "Please check your .env file and ensure all required API keys are set."
        )

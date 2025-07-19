"""
config_agent.py: Handles environment variable loading, API key setup, and logging configuration.
- This module does not use ToolInfo, LLM prompts, or LLM input truncation constants directly.
"""
import os
import dotenv
import logging
from typing import Optional

def setup_logging() -> None:
    """
    Configure logging for the AI Tool Discovery Agent.
    
    Sets up basic logging configuration with timestamp and level formatting.
    Reduces noise from third-party libraries by setting their log levels to WARNING.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

def validate_critical_config() -> None:
    """
    Validate that all critical API keys and configuration are present.
    
    Raises:
        ValueError: If any critical configuration is missing with helpful error messages.
    """
    missing_configs = []
    
    if not AZURE_OPENAI_ENDPOINT:
        missing_configs.append("AZURE_OPENAI_ENDPOINT")
    if not AZURE_OPENAI_KEY:
        missing_configs.append("AZURE_OPENAI_KEY")
    if not SERPER_API_KEY:
        missing_configs.append("SERPER_API_KEY")
    if not SERPAPI_API_KEY:
        missing_configs.append("SERPAPI_API_KEY")
    
    if missing_configs:
        error_msg = (
            f"Missing critical configuration: {', '.join(missing_configs)}. "
            "Please check your .env file and ensure all required API keys are set."
        )
        raise ValueError(error_msg)

# Load environment variables from .env file
dotenv.load_dotenv()

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT: Optional[str] = os.environ.get('AZURE_OPENAI_ENDPOINT')
"""
Azure OpenAI service endpoint URL.
Required for all LLM operations (field extraction, summarization, classification).
Example: 'https://your-resource.openai.azure.com/'
"""

AZURE_OPENAI_KEY: Optional[str] = os.environ.get('AZURE_OPENAI_KEY')
"""
Azure OpenAI API key for authentication.
Required for all LLM operations. Should be kept secure and not committed to version control.
"""

AZURE_OPENAI_DEPLOYMENT: Optional[str] = os.environ.get('AZURE_OPENAI_DEPLOYMENT')
"""
Azure OpenAI deployment name (e.g., 'gpt-4o', 'gpt-35-turbo').
If not set, defaults to 'gpt-4o' in llm_utils_agent.py.
Example: 'gpt-4o'
"""

# Search API Configuration
SERPER_API_KEY: Optional[str] = os.environ.get('SERPER_API_KEY')
"""
Serper.dev API key for web search functionality.
Required for async web search operations. Used as primary search engine.
Get your key at: https://serper.dev/
"""

SERPAPI_API_KEY: Optional[str] = os.environ.get('SERPAPI_API_KEY')
"""
SerpAPI key for web search functionality.
Required for web search operations. Used as secondary search engine.
Get your key at: https://serpapi.com/
""" 
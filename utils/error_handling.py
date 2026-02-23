from typing import Optional, Dict


class AgentError(Exception):
    """Base exception for all custom errors in the AI Tool Discovery Agent."""

    def __init__(self, message: str = "", context: Optional[Dict] = None) -> None:
        super().__init__(message)
        self.context = context or {}


class ScrapingError(AgentError):
    """Raised for errors during HTML fetching (network, HTTP status, etc.)."""
    pass


class ExtractionError(AgentError):
    """Raised for errors during LLM-based extraction or JSON parsing."""
    pass


class ConfigError(AgentError):
    """Raised for configuration or environment variable errors."""
    pass

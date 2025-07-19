from typing import Optional, Dict

class AgentError(Exception):
    """
    Base exception for all custom errors in the AI Tool Discovery Agent.
    Optionally accepts a message and context for debugging.
    """
    def __init__(self, message: str = "", context: Optional[Dict] = None):
        super().__init__(message)
        self.context = context if context is not None else {}

class ScrapingError(AgentError):
    """
    Exception raised for errors during scraping (network, parsing, etc).
    Optionally accepts a message and context.
    """
    pass

class ExtractionError(AgentError):
    """
    Exception raised for errors during LLM extraction or parsing.
    Optionally accepts a message and context.
    """
    pass

class ConfigError(AgentError):
    """
    Exception raised for configuration or environment errors.
    Optionally accepts a message and context.
    """
    pass 
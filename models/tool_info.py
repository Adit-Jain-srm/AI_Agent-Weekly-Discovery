from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class ToolInfo:
    """
    Data class representing structured information about an AI tool.
    """
    title: str
    website: str
    summary: Optional[str]
    features: List[str] = field(default_factory=list)
    pricing: Optional[str] = None
    source: str = ""
    target_audience: Optional[str] = None
    main_text: str = ""
    ai_tool_annotation: Optional[str] = None
    tags: Optional[List[str]] = field(default_factory=list)
    publish_date: Optional[str] = None  # ISO 8601 date string (YYYY-MM-DD) if available 
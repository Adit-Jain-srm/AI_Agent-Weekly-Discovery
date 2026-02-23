from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ToolInfo:
    """Structured information about a discovered AI tool."""

    title: str
    website: str
    summary: Optional[str] = None
    features: List[str] = field(default_factory=list)
    pricing: Optional[str] = None
    source: str = ""
    target_audience: Optional[str] = None
    main_text: str = ""
    ai_tool_annotation: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    publish_date: Optional[str] = None

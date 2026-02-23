from models.tool_info import ToolInfo
from typing import List


def print_tool_info(tool: ToolInfo, idx: int) -> None:
    """Print formatted information for a single discovered tool."""
    print(f"\n{idx}. {tool.title or 'N/A'}")

    if tool.website != tool.source:
        print(f"   Website:  {tool.website}")
    print(f"   Source:   {tool.source}")
    print(f"   Summary:  {tool.summary or 'N/A'}")

    if tool.features:
        print(f"   Features: {', '.join(tool.features[:3])}")
    if tool.pricing:
        print(f"   Pricing:  {tool.pricing}")

    print("-" * 60)


def print_summary(tools: List[ToolInfo]) -> None:
    """Print all discovered tools and a total count."""
    print("=== AI Tool Discovery Results ===")
    for i, tool in enumerate(tools, 1):
        print_tool_info(tool, i)
    print(f"\nTotal AI Tools Discovered: {len(tools)}")

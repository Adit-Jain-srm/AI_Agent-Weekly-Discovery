from models.tool_info import ToolInfo
from typing import List

def print_tool_info(tool: ToolInfo, idx: int) -> None:
    print(f"\n{idx}. {getattr(tool, 'title', 'N/A')}")
    website = getattr(tool, 'website', 'N/A')
    source = getattr(tool, 'source', 'N/A')
    if website != source:
        print(f"   Website: {website}")
    print(f"   Source: {source}")
    print(f"   Summary: {getattr(tool, 'summary', 'N/A')}")
    if getattr(tool, 'features', None):
        print(f"   Features: {', '.join(getattr(tool, 'features', [])[:3])}")
    if getattr(tool, 'pricing', None):
        print(f"   Pricing: {getattr(tool, 'pricing', 'N/A')}")
    print('-' * 60)

def print_summary(tools: List[ToolInfo]) -> None:
    print("=== AI Tool Discovery Results ===")
    for i, tool in enumerate(tools, 1):
        print_tool_info(tool, i)
    print(f"\nTotal AI Tools Discovered: {len(tools)}") 
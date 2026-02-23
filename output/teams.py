import logging
import re

import requests

from models.tool_info import ToolInfo

_GENERIC_FEATURES = frozenset({
    "BPO Services", "Consultation", "Talent Outsourcing",
    "International Logistics BPO", "E-Recovery", "Process Automation", "Services",
})


def format_tool_for_teams(tool: ToolInfo, idx: int) -> str:
    """Format a ToolInfo as a Markdown message suitable for Microsoft Teams."""
    features = list(dict.fromkeys(tool.features or []))
    features = [f for f in features if f not in _GENERIC_FEATURES and len(f) > 5]
    features_str = "\n".join(f"- {f}" for f in features) if features else "N/A"

    pricing = tool.pricing
    if not pricing or len(str(pricing).split()) > 20 or (isinstance(pricing, str) and "revolution" in pricing.lower()):
        pricing = "No pricing information available."

    overview = tool.summary or (tool.main_text[:300] if tool.main_text else "")
    if overview:
        sentences = re.split(r"(?<=[.!?]) +", overview)
        if len(sentences) > 5:
            overview = " ".join(sentences[:5])
        elif len(overview.split()) > 80:
            overview = " ".join(overview.split()[:80]) + "..."
    overview = overview or "N/A"

    target = tool.target_audience if tool.target_audience and len(tool.target_audience) >= 3 else "N/A"

    tags_str = ", ".join(tool.tags) if tool.tags else "N/A"

    website_line = f"**\U0001f310 Website:** [{tool.website}]({tool.website})\n\n" if tool.website != tool.source else ""

    return (
        f"### \U0001f680 AI Tool {idx}: {tool.title or 'N/A'}\n\n"
        f"{website_line}"
        f"**\U0001f517 Source:** [{tool.source}]({tool.source})\n\n"
        f"**\U0001f3af Target Audience / Use Case:** {target}\n\n"
        f"**\U0001f4dd Overview:**\n{overview}\n\n"
        f"**\U0001f4a1 Key Features:**\n{features_str}\n\n"
        f"**\U0001f4b2 Pricing:** {pricing}\n\n"
    )


def send_tool_to_teams(tool: ToolInfo, idx: int, webhook_url: str) -> None:
    """Post a formatted tool message to Microsoft Teams via webhook."""
    if not webhook_url:
        logging.warning("TEAMS_WEBHOOK_URL not set. Skipping Teams notification.")
        return

    payload = {"text": format_tool_for_teams(tool, idx)}
    try:
        response = requests.post(webhook_url, json=payload, timeout=15)
        if response.status_code == 200:
            logging.info(f"Tool {idx} sent to Microsoft Teams successfully.")
        else:
            logging.error(f"Failed to send tool {idx} to Teams: {response.status_code} {response.text}")
    except requests.RequestException as e:
        logging.error(f"Teams webhook request failed for tool {idx}: {e}")

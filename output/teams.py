from models.tool_info import ToolInfo
import requests
import re

def format_tool_for_teams(tool: ToolInfo, idx: int) -> str:
    features = list(dict.fromkeys(getattr(tool, 'features', [])))
    GENERIC_FEATURES = {"BPO Services", "Consultation", "Talent Outsourcing", "International Logistics BPO", "E-Recovery", "Process Automation", "Services"}
    features = [f for f in features if f not in GENERIC_FEATURES and len(f) > 5]
    features_str = "\n".join(f"- {f}" for f in features) if features else "N/A"

    pricing = getattr(tool, 'pricing', None)
    if not pricing or len(str(pricing).split()) > 20 or (isinstance(pricing, str) and 'revolution' in pricing.lower()):
        pricing = "No pricing information available."

    overview = getattr(tool, 'summary', None) or getattr(tool, 'main_text', '')[:300]
    if overview:
        sentences = re.split(r'(?<=[.!?]) +', overview)
        if len(sentences) > 5:
            overview = ' '.join(sentences[:5])
        else:
            words = overview.split()
            if len(words) > 80:
                overview = ' '.join(words[:80]) + '...'
    if not overview:
        overview = "N/A"

    target = getattr(tool, 'target_audience', None)
    if not target or len(target) < 3:
        target = "N/A"

    tags = getattr(tool, 'tags', None)
    tags_str = ", ".join(tags) if tags else "N/A"

    website = getattr(tool, 'website', 'N/A')
    source = getattr(tool, 'source', 'N/A')
    website_line = f"**🌐 Website:** [{website}]({website})\n\n" if website != source else ""

    return (
        f"### 🚀 AI Tool {idx}: {getattr(tool, 'title', 'N/A')}\n\n"
        f"{website_line}"
        f"**🔗 Source:** [{source}]({source})\n\n"
        f"**🎯 Target Audience / Use Case:** {target}\n\n"
        f"**📝 Overview:**\n{overview}\n\n"
        f"**💡 Key Features:**\n{features_str}\n\n"
        f"**💲 Pricing:** {pricing}\n\n"
    )

def send_tool_to_teams(tool: ToolInfo, idx: int, webhook_url: str) -> None:
    if not webhook_url:
        print("TEAMS_WEBHOOK_URL not set. Skipping Teams notification.")
        return
    payload = {"text": format_tool_for_teams(tool, idx)}
    response = requests.post(webhook_url, json=payload)
    if response.status_code == 200:
        print(f"Message for tool {idx} sent to Microsoft Teams successfully.")
    else:
        print(f"Failed to send message for tool {idx} to Teams: {response.status_code} {response.text}") 
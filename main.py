"""
main.py: Entry point. Sets up logging, runs the 100% LLM-based AI Tool Discovery pipeline, prints results, and optionally posts to Teams.
- All tool info extraction, summarization, and classification is performed in a single GPT-4o (Azure OpenAI) call per tool using ToolInfo from models.tool_info and prompts from prompts/ loaded via utils/prompt_loader.
- All HTTP headers, search queries, and other constants are set in config/constants.py.
"""
import os
from agents.config_agent import setup_logging
from agents.pipeline_agent import run_pipeline
from models.tool_info import ToolInfo
from output.console import print_summary
from output.teams import send_tool_to_teams
import re

TEAMS_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL")

if __name__ == "__main__":
    setup_logging()
    print("Running AI Tool Discovery Agent...")
    import asyncio
    tools = asyncio.run(run_pipeline())
    print_summary(tools)
    # Optionally send to Teams if webhook is set
    for i, tool in enumerate(tools, 1):
        if getattr(tool, 'ai_tool_annotation', None) == 'ai_tool':
            send_tool_to_teams(tool, i, TEAMS_WEBHOOK_URL or "")
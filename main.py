"""
main.py: Entry point for the AI Tool Discovery Agent.
Sets up logging, runs the async pipeline, prints results, and optionally posts to Microsoft Teams.
"""
import asyncio
import os

from agents.config_agent import setup_logging, validate_critical_config
from agents.pipeline_agent import run_pipeline
from output.console import print_summary
from output.teams import send_tool_to_teams

TEAMS_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL")


def main() -> None:
    setup_logging()
    validate_critical_config()

    print("Running AI Tool Discovery Agent...")
    tools = asyncio.run(run_pipeline())
    print_summary(tools)

    if TEAMS_WEBHOOK_URL:
        for i, tool in enumerate(tools, 1):
            if tool.ai_tool_annotation == "ai_tool":
                send_tool_to_teams(tool, i, TEAMS_WEBHOOK_URL)


if __name__ == "__main__":
    main()

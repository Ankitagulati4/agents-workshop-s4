"""
HOMEWORK 1 — Build YOUR OWN Useful MCP Server
=============================================
Use this template to build an MCP server for an API you use daily.

Ideas:
  - Notion / Confluence    (notes, wiki, docs)
  - Jira / Linear          (tickets, projects)
  - Slack                  (search messages, post)
  - Your company's own API
  - Any REST API with an SDK

Instructions:
  1. Pick an API
  2. Fill in the TODOs below
  3. Add at least 3 @mcp.tool() functions
  4. Add 1 @mcp.resource()
  5. Test with: mcp dev starter.py

Time: ~50 minutes
"""

import os
from dotenv import load_dotenv
load_dotenv(override=True)

from mcp.server.fastmcp import FastMCP

# TODO: import your API SDK here
# from notion_client import Client   # example
# import requests                    # for raw REST

# ── Server setup ──────────────────────────────────────────────────────────────
# TODO: give your server a meaningful name and instructions
mcp = FastMCP(
    name="[YOUR_API] MCP Server",     # ← change this
    instructions=(
        "[Describe what this server does in 1–2 sentences. "
        "This text appears in the LLM context to explain when to use these tools.]"
    ),
)

# TODO: load your API credentials from .env
API_KEY = os.getenv("YOUR_API_KEY", "")


# ── Tool 1 ────────────────────────────────────────────────────────────────────
@mcp.tool()
async def tool_one(param1: str, param2: str = "") -> str:
    """[One-line description of what this tool does.

    Use this when [describe the user intent that should trigger this tool].

    Args:
        param1: [description of param1]
        param2: [description of param2, if optional say: Optional. Default is '']

    Returns:
        [Describe the format of the return value]
    """
    # TODO: implement
    if not API_KEY:
        return "Error: YOUR_API_KEY not set in .env"

    # Your API call here
    return f"[Tool 1 result for param1={param1}]"


# ── Tool 2 ────────────────────────────────────────────────────────────────────
@mcp.tool()
async def tool_two(query: str) -> str:
    """[One-line description.]

    Use this when [user intent].
    """
    # TODO: implement
    return f"[Tool 2 result for query={query}]"


# ── Tool 3 ────────────────────────────────────────────────────────────────────
@mcp.tool()
async def tool_three(item_id: str) -> str:
    """[One-line description.]

    Use this when [user intent].
    """
    # TODO: implement
    return f"[Tool 3 result for item_id={item_id}]"


# ── Resource ──────────────────────────────────────────────────────────────────
@mcp.resource("myapi://info")
async def get_info() -> str:
    """Information about the connected API account/workspace."""
    # TODO: return useful context (account name, workspace, available spaces, etc.)
    return "[Your API account info here]"


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not API_KEY:
        print("⚠️  YOUR_API_KEY not set in .env")
    print("Starting MCP server...")
    print("Test with: mcp dev starter.py\n")
    mcp.run(transport="stdio")

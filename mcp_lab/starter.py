"""
LAB 2 — Build a Python MCP Server from Scratch
===============================================
Goal:
  Create a working MCP server with:
    - 2 Tools    (calculate, summarise_url)
    - 1 Resource (help page)
    - 1 Prompt   (analysis_prompt)
  Then test it live using the MCP Inspector.

Steps:
  1. pip install mcp[cli] httpx
  2. Instantiate FastMCP
  3. Add @mcp.tool()      calculate(expression)
  4. Add @mcp.tool()      summarise_url(url)
  5. Add @mcp.resource()  help text
  6. Add @mcp.prompt()    analysis_prompt(topic)
  7. Run: mcp dev starter.py
     → Browser opens at http://localhost:5173 (MCP Inspector)
     → Call each tool manually and verify

Time: ~20 minutes
Tip:  mcp dev <file> hot-reloads on save — no need to restart
"""

import ast
import os
import httpx
from dotenv import load_dotenv
load_dotenv(override=True)

# ── TODO 1 ─────────────────────────────────────────────────────────────────────
# Import FastMCP and create your server instance.
#
# from mcp.server.fastmcp import FastMCP
# mcp = FastMCP("MyServer")         ← give it a meaningful name

# TODO: import and instantiate here


# ── TODO 2 ─────────────────────────────────────────────────────────────────────
# Register a Tool: calculate
#
# @mcp.tool()
# async def calculate(expression: str) -> str:
#     """Safely evaluate a mathematical expression and return the result.
#     Supports: +, -, *, /, **, //, %, parentheses, and numeric literals.
#     Examples: '2 + 2', '(10 * 3) / 4', '2 ** 8'
#     """
#
# IMPORTANT: Use ast.literal_eval — NEVER use eval() directly (security risk).
# For proper math, parse with ast and walk the tree, OR use a safe subset.
# Simple approach: try ast.literal_eval first; if it fails, return an error.
# Better approach: use the _safe_eval() helper below.

def _safe_eval(expr: str):
    """Walk an AST and only allow safe numeric operations."""
    ALLOWED_NODES = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
        ast.Mod, ast.Pow, ast.USub, ast.UAdd,
    )
    tree = ast.parse(expr.strip(), mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"Disallowed operation: {type(node).__name__}")
    return eval(compile(tree, "<string>", "eval"))  # noqa: S307 — safe after walk


# TODO: implement @mcp.tool() calculate here


# ── TODO 3 ─────────────────────────────────────────────────────────────────────
# Register a Tool: summarise_url
#
# @mcp.tool()
# async def summarise_url(url: str) -> str:
#     """Fetch a URL and return the first 500 characters of its text content.
#     Useful for quickly previewing the content of a web page or API endpoint.
#     """
#
# Use httpx.AsyncClient to fetch the URL.
# Strip HTML tags with a simple regex or just return raw text.
# Handle errors gracefully (connection errors, 4xx/5xx responses).
#
# Hint:
#   async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
#       r = await client.get(url)
#       ...

# TODO: implement @mcp.tool() summarise_url here


# ── TODO 4 ─────────────────────────────────────────────────────────────────────
# Register a Resource: help text
#
# Resources are read-only data the LLM can access.
# URI format: "scheme://path"   e.g. "myserver://help"
#
# @mcp.resource("myserver://help")
# async def get_help() -> str:
#     """Returns documentation about what this MCP server can do."""
#     return "..."    ← describe your server's tools here

# TODO: implement @mcp.resource() here


# ── TODO 5 ─────────────────────────────────────────────────────────────────────
# Register a Prompt: analysis_prompt
#
# Prompts are reusable system prompt templates with parameters.
#
# @mcp.prompt()
# def analysis_prompt(topic: str) -> str:
#     """Generate a thorough analysis prompt for any topic."""
#     return f"..."   ← a system prompt instructing the LLM how to analyse {topic}

# TODO: implement @mcp.prompt() here


# ── TODO 6 ─────────────────────────────────────────────────────────────────────
# Run the server.
#
# For MCP Inspector (testing in browser):
#   mcp.run(transport="stdio")
#
# For HTTP/SSE (remote clients):
#   mcp.run(transport="sse", host="0.0.0.0", port=8000)
#
# When you run `mcp dev starter.py`, it automatically uses stdio + opens the Inspector.

# TODO: add the if __name__ == "__main__": block with mcp.run()

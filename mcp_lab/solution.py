"""
LAB 2 SOLUTION — Python MCP Server: Tools, Resources & Prompts
==============================================================
Complete working MCP server. Read only after attempting starter.py!

Test with:
    mcp dev solution.py          ← opens Inspector at localhost:5173
    mcp dev solution.py --port 5174   ← if 5173 is busy

Connect to Claude Desktop (optional):
    See claude_desktop_config.json in this folder.
"""

import ast
import re
import os
import httpx
from dotenv import load_dotenv
load_dotenv(override=True)

from mcp.server.fastmcp import FastMCP

# ── Create the server ─────────────────────────────────────────────────────────
mcp = FastMCP(
    name="Workshop MCP Server",
    instructions=(
        "This server provides tools for math calculation, URL content preview, "
        "and analysis prompts. Use 'calculate' for any math expressions, "
        "'summarise_url' to quickly inspect a web page."
    ),
)


# ── Helper: safe math evaluator ────────────────────────────────────────────────
def _safe_eval(expr: str) -> float:
    """Evaluate a math expression safely using AST (no exec/eval of arbitrary code)."""
    ALLOWED = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
        ast.Mod, ast.Pow, ast.USub, ast.UAdd,
    )
    tree = ast.parse(expr.strip(), mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED):
            raise ValueError(f"Operation not allowed: {type(node).__name__}")
    return eval(compile(tree, "<string>", "eval"))  # noqa: S307


# ── Tool 1: calculate ──────────────────────────────────────────────────────────
@mcp.tool()
async def calculate(expression: str) -> str:
    """Safely evaluate a mathematical expression and return the result.

    Supports: +, -, *, /, ** (power), // (floor div), % (modulo), parentheses.
    Does NOT support: variables, functions, imports, or any code execution.

    Args:
        expression: A math expression string, e.g. '(2 + 3) * 4' or '2 ** 10'

    Returns:
        The numeric result as a string, or an error message.
    """
    try:
        result = _safe_eval(expression)
        # Format nicely: integers without .0, floats with up to 6 sig figs
        if isinstance(result, float) and result.is_integer():
            return f"{expression} = {int(result)}"
        return f"{expression} = {round(result, 6)}"
    except (ValueError, SyntaxError, TypeError) as e:
        return f"Error evaluating '{expression}': {e}"
    except ZeroDivisionError:
        return f"Error: division by zero in '{expression}'"


# ── Tool 2: summarise_url ──────────────────────────────────────────────────────
@mcp.tool()
async def summarise_url(url: str, max_chars: int = 500) -> str:
    """Fetch a URL and return a preview of its text content.

    Strips HTML tags and returns the first max_chars characters of plain text.
    Useful for quickly previewing web pages, API docs, or JSON endpoints.

    Args:
        url:       The URL to fetch (must start with http:// or https://)
        max_chars: Maximum characters to return (default 500, max 2000)

    Returns:
        First max_chars characters of the page's text content, or an error.
    """
    if not url.startswith(("http://", "https://")):
        return "Error: URL must start with http:// or https://"

    max_chars = min(max_chars, 2000)  # safety cap

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "MCPBot/1.0"})
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")

        if "json" in content_type:
            # Format JSON nicely
            import json
            try:
                data = response.json()
                text = json.dumps(data, indent=2)
            except Exception:
                text = response.text
        else:
            # Strip HTML tags
            text = re.sub(r"<[^>]+>", " ", response.text)
            text = re.sub(r"\s+", " ", text).strip()

        preview = text[:max_chars]
        suffix  = f"... [truncated — total {len(text)} chars]" if len(text) > max_chars else ""
        return f"[{response.status_code} {url}]\n\n{preview}{suffix}"

    except httpx.TimeoutException:
        return f"Error: Request to {url} timed out after 10 seconds"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} from {url}"
    except Exception as e:
        return f"Error fetching {url}: {type(e).__name__}: {e}"


# ── Resource: help page ────────────────────────────────────────────────────────
@mcp.resource("myserver://help")
async def get_help() -> str:
    """Server documentation — what this MCP server can do."""
    return """# Workshop MCP Server — Help

## Available Tools

### calculate(expression)
Safely evaluates mathematical expressions.
- Supported: +, -, *, /, **, //, %, parentheses
- Example: calculate("(100 * 1.08) / 4")

### summarise_url(url, max_chars=500)
Fetches a URL and returns a text preview.
- Works with web pages, JSON APIs, plain text files
- Example: summarise_url("https://api.github.com/repos/langchain-ai/langchain")

## Available Prompts

### analysis_prompt(topic)
Generates a structured analysis prompt for any topic.

## Notes
- This is a demo server built during the Session 4 workshop
- Tools run locally — no sensitive data is sent externally
"""


# ── Prompt: analysis template ──────────────────────────────────────────────────
@mcp.prompt()
def analysis_prompt(topic: str) -> str:
    """Generate a thorough, structured analysis prompt for any topic.

    Args:
        topic: The subject to be analysed (e.g. 'LangGraph', 'MCP protocol')
    """
    return f"""You are a senior technical analyst. Provide a comprehensive analysis of: {topic}

Structure your response as follows:

## 1. Executive Summary (2–3 sentences)
What is {topic} and why does it matter?

## 2. Core Concepts
List and explain the 3–5 most important concepts or components.

## 3. Key Strengths
What does {topic} do particularly well? Use specific examples.

## 4. Limitations & Trade-offs
What are the known weaknesses or situations where {topic} is not the right choice?

## 5. Comparison with Alternatives
How does {topic} compare to 2–3 alternatives? Use a brief comparison table.

## 6. Practical Use Cases
Describe 3 real-world scenarios where {topic} would be the right tool.

## 7. Getting Started
What are the first 3 steps someone should take to start using {topic}?

Be specific, use concrete examples, and avoid vague generalities."""


# ── Run the server ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    if transport == "sse":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        print(f"Starting MCP server via HTTP+SSE on port {port}")
        print(f"Inspector: http://localhost:{port}/docs")
        mcp.run(transport="sse", host="0.0.0.0", port=port)
    else:
        # stdio mode — used by `mcp dev` and Claude Desktop
        mcp.run(transport="stdio")

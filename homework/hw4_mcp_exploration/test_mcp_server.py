"""
HW4 — MCP Server Test Script
==============================
Verifies that any Python MCP server is working correctly
by calling its tools and checking responses.

Usage:
    # Test the Lab 2 solution
    python test_mcp_server.py --server ../mcp_lab/solution.py

    # Test a custom server
    python test_mcp_server.py --server path/to/your_server.py

What it checks:
  1. Server starts without errors
  2. tools/list returns at least 1 tool
  3. Each tool can be called and returns a non-empty string
  4. resources/list returns resources (if any)
  5. prompts/list returns prompts (if any)
"""

import asyncio
import sys
import argparse
import subprocess
import json
import time
from pathlib import Path

PASS, FAIL, WARN = "✅", "❌", "⚠️ "


async def test_server_via_mcp_client(server_path: str):
    """Use the MCP Python client to test a server end-to-end."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    server_params = StdioServerParameters(
        command="python",
        args=[str(Path(server_path).resolve())],
    )

    results = {"tools": [], "resources": [], "prompts": [], "errors": []}

    print(f"\n  Connecting to: {server_path}")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print(f"  {PASS}  Server started and initialised")

                # ── List tools ────────────────────────────────────────────────
                tools_response = await session.list_tools()
                tools = tools_response.tools
                print(f"\n  Tools ({len(tools)} found):")
                for tool in tools:
                    print(f"    • {tool.name}: {tool.description[:60]}...")
                    results["tools"].append(tool.name)

                if not tools:
                    print(f"  {WARN}  No tools registered — is this intentional?")

                # ── Call each tool with dummy args ─────────────────────────────
                print(f"\n  Calling each tool with test inputs:")
                for tool in tools:
                    try:
                        # Build minimal args from schema
                        schema     = tool.inputSchema or {}
                        properties = schema.get("properties", {})
                        required   = schema.get("required", [])
                        test_args  = {}

                        for prop_name, prop_def in properties.items():
                            prop_type = prop_def.get("type", "string")
                            if prop_name in required or True:
                                if prop_type == "string":
                                    # Use sensible defaults for known arg names
                                    defaults = {
                                        "expression": "2 + 2",
                                        "url":        "https://httpbin.org/json",
                                        "topic":      "MCP protocol",
                                        "city":       "London",
                                        "text":       "Hello world from the MCP test suite.",
                                        "query":      "LangChain",
                                    }
                                    test_args[prop_name] = defaults.get(prop_name, "test_value")
                                elif prop_type in ("integer", "number"):
                                    test_args[prop_name] = prop_def.get("default", 10)
                                elif prop_type == "boolean":
                                    test_args[prop_name] = prop_def.get("default", True)

                        result = await session.call_tool(tool.name, test_args)
                        content = result.content[0].text if result.content else ""

                        if content:
                            preview = content[:80].replace("\n", " ")
                            print(f"    {PASS}  {tool.name}({test_args}) → '{preview}...'")
                        else:
                            print(f"    {WARN}  {tool.name} returned empty response")

                    except Exception as e:
                        print(f"    {FAIL}  {tool.name} raised: {e}")
                        results["errors"].append(f"{tool.name}: {e}")

                # ── List resources ─────────────────────────────────────────────
                try:
                    resources_response = await session.list_resources()
                    resources = resources_response.resources
                    print(f"\n  Resources ({len(resources)} found):")
                    for r in resources:
                        print(f"    • {r.uri}: {r.name}")
                        results["resources"].append(str(r.uri))
                except Exception as e:
                    print(f"\n  {WARN}  Could not list resources: {e}")

                # ── List prompts ───────────────────────────────────────────────
                try:
                    prompts_response = await session.list_prompts()
                    prompts = prompts_response.prompts
                    print(f"\n  Prompts ({len(prompts)} found):")
                    for p in prompts:
                        print(f"    • {p.name}: {p.description or '(no description)'}")
                        results["prompts"].append(p.name)
                except Exception as e:
                    print(f"\n  {WARN}  Could not list prompts: {e}")

    except FileNotFoundError:
        print(f"  {FAIL}  Server file not found: {server_path}")
        results["errors"].append("File not found")
    except Exception as e:
        print(f"  {FAIL}  Server failed to start: {e}")
        results["errors"].append(f"Startup error: {e}")

    return results


def print_summary(results: dict):
    print(f"\n{'='*62}")
    print("  TEST SUMMARY")
    print('='*62)
    print(f"  Tools registered:     {len(results['tools'])}")
    print(f"  Resources registered: {len(results['resources'])}")
    print(f"  Prompts registered:   {len(results['prompts'])}")
    print(f"  Errors encountered:   {len(results['errors'])}")

    if results["errors"]:
        print(f"\n  Errors:")
        for e in results["errors"]:
            print(f"    {FAIL} {e}")

    if not results["errors"] and results["tools"]:
        print(f"\n  {PASS}  All checks passed! Server is working correctly.")
        print(f"\n  Next step: run 'mcp dev {sys.argv[-1]}' to test in the browser Inspector.")
    elif not results["tools"]:
        print(f"\n  {WARN}  No tools found. Add at least one @mcp.tool() to your server.")
    else:
        print(f"\n  {WARN}  Some checks failed — review errors above.")


async def main(server_path: str):
    print("="*62)
    print("MCP Server Test Runner — Session 4 Homework 4")
    print("="*62)

    results = await test_server_via_mcp_client(server_path)
    print_summary(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test any Python MCP server")
    parser.add_argument(
        "--server",
        default="../mcp_lab/solution.py",
        help="Path to the MCP server Python file (default: ../mcp_lab/solution.py)"
    )
    args = parser.parse_args()

    try:
        from mcp import ClientSession
    except ImportError:
        print(f"{FAIL} mcp package not installed. Run: pip install mcp[cli]")
        sys.exit(1)

    asyncio.run(main(args.server))

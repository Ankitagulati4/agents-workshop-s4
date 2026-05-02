# HOMEWORK 4 — MCP Ecosystem Exploration Guide
## Install, test, and document 2 community MCP servers

---

## Your Task

Install 2 MCP servers from the official list, connect them to Claude Desktop
or the MCP Inspector, and document what works, what breaks, and what surprised you.

---

## Step 1 — Pick Two Servers

Browse these sources and pick 2 servers that interest you:

| Source | URL |
|--------|-----|
| Official Anthropic servers | https://github.com/modelcontextprotocol/servers |
| Community directory | https://mcp.so |
| Smithery marketplace | https://smithery.ai |

**Recommended starter picks (low friction, work reliably):**

| Server | What it does | Install |
|--------|--------------|---------|
| `@modelcontextprotocol/server-filesystem` | Read/write local files | `npx @modelcontextprotocol/server-filesystem /path/to/dir` |
| `@modelcontextprotocol/server-fetch` | Fetch URLs + convert HTML to Markdown | `npx @modelcontextprotocol/server-fetch` |
| `@modelcontextprotocol/server-memory` | Persistent key-value memory for Claude | `npx @modelcontextprotocol/server-memory` |
| `@modelcontextprotocol/server-brave-search` | Web search (needs Brave API key) | `npx @modelcontextprotocol/server-brave-search` |
| `mcp-server-github` (PyPI) | GitHub integration | `pip install mcp-server-github` |

---

## Step 2 — Install and Test with MCP Inspector

For Node.js servers (npx):
```bash
# Install Node.js 18+ first if needed: nodejs.org
npx -y @modelcontextprotocol/server-fetch
```

For Python servers:
```bash
pip install mcp-server-github   # example
mcp dev $(python -m mcp_server_github)
```

The MCP Inspector opens at **http://localhost:5173**.

---

## Step 3 — Connect to Claude Desktop (Optional but Recommended)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/YOUR_USERNAME/Desktop"
      ]
    },
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    }
  }
}
```

Restart Claude Desktop → look for the 🔨 (tools) icon in the chat bar.

---

## Step 4 — Test Script

Run `python test_mcp_servers.py` to verify your Python MCP server works
correctly before connecting to Claude Desktop.

```bash
python test_mcp_servers.py --server path/to/your_server.py
```

---

## Step 5 — Fill In Your Findings

Copy the table below into a new file `my_findings.md` and complete it.

### Server 1: [Name]
| Question | Your Answer |
|----------|-------------|
| What does it do? | |
| Install command | |
| Tools it exposes | |
| Resources it exposes | |
| Did it work first try? | Yes / No |
| What broke? | |
| What surprised you? | |
| Would you use it in production? | Yes / No / Maybe |
| Why? | |

### Server 2: [Name]
| Question | Your Answer |
|----------|-------------|
| What does it do? | |
| Install command | |
| Tools it exposes | |
| Resources it exposes | |
| Did it work first try? | Yes / No |
| What broke? | |
| What surprised you? | |
| Would you use it in production? | Yes / No / Maybe |
| Why? | |

---

## Discussion Questions (Bring to Next Session)

1. What's the biggest limitation you hit with community MCP servers?
2. How would you version-control and test an MCP server you wrote for your team?
3. If you were building a company-wide MCP server, what security controls would you add?
4. The MCP spec is still v1.x — what features do you think are missing?

---

## Useful Commands

```bash
# List all tools a server exposes (without Inspector)
mcp dev your_server.py --inspect-only

# Run server in SSE mode for HTTP testing
python your_server.py sse 8000

# curl test for SSE server
curl -X POST http://localhost:8000/tools/list \
  -H "Content-Type: application/json" \
  -d '{}'
```

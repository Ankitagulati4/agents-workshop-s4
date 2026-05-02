"""
HOMEWORK 1 — Build a Useful MCP Server: GitHub Integration
==========================================================
A production-style MCP server with 5 tools connecting to the GitHub API.

Tools:
  1. list_repos        — list your repos (with filtering)
  2. get_repo_info     — detailed info about a specific repo
  3. list_issues       — list open issues on a repo
  4. create_issue      — create a new issue
  5. search_code       — search code across GitHub

Resource:
  github://profile     — your GitHub profile summary

Requirements:
  - GITHUB_TOKEN in .env (github.com/settings/tokens → fine-grained PAT)
  - GITHUB_REPO in .env  (e.g. "username/repo-name")
  - pip install PyGithub mcp[cli]

Test:
    mcp dev github_mcp_server.py

Connect to Claude Desktop:
    See ../mcp_lab/claude_desktop_config.json for instructions.
"""

import os
from dotenv import load_dotenv
load_dotenv(override=True)

from mcp.server.fastmcp import FastMCP
from github import Github, GithubException

# ── Server setup ──────────────────────────────────────────────────────────────
mcp = FastMCP(
    name="GitHub MCP Server",
    instructions=(
        "This server provides tools to interact with GitHub: list repositories, "
        "get repo info, manage issues, and search code. "
        "Always use get_repo_info before creating issues to confirm the repo exists."
    ),
)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
DEFAULT_REPO  = os.getenv("GITHUB_REPO", "")

def _get_client() -> Github:
    if not GITHUB_TOKEN:
        raise ValueError(
            "GITHUB_TOKEN not set. Add it to .env: "
            "github.com/settings/tokens → Generate new token (fine-grained)"
        )
    return Github(GITHUB_TOKEN)


# ── Tool 1: list_repos ────────────────────────────────────────────────────────
@mcp.tool()
async def list_repos(
    language: str = "",
    max_results: int = 10,
    sort_by: str = "updated",
) -> str:
    """List your GitHub repositories.

    Args:
        language:    Filter by programming language (e.g. 'python', 'javascript').
                     Leave empty for all languages.
        max_results: Maximum number of repos to return (default 10, max 50).
        sort_by:     Sort order: 'updated', 'created', 'pushed', or 'full_name'.

    Returns:
        Formatted list of repositories with name, language, stars, and description.
    """
    try:
        g    = _get_client()
        user = g.get_user()
        repos = list(user.get_repos(sort=sort_by))

        if language:
            repos = [r for r in repos if (r.language or "").lower() == language.lower()]

        repos = repos[:min(max_results, 50)]

        if not repos:
            return f"No repositories found{f' with language={language}' if language else ''}."

        lines = [f"Found {len(repos)} repos:\n"]
        for r in repos:
            lines.append(
                f"• {r.full_name}\n"
                f"  Language: {r.language or 'N/A'}  "
                f"Stars: {r.stargazers_count}  "
                f"Updated: {r.updated_at.strftime('%Y-%m-%d')}\n"
                f"  {r.description or '(no description)'}\n"
            )
        return "\n".join(lines)

    except GithubException as e:
        return f"GitHub API error: {e.status} — {e.data.get('message', str(e))}"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


# ── Tool 2: get_repo_info ─────────────────────────────────────────────────────
@mcp.tool()
async def get_repo_info(repo_name: str = "") -> str:
    """Get detailed information about a GitHub repository.

    Args:
        repo_name: Full repo name as 'owner/repo' (e.g. 'langchain-ai/langchain').
                   Defaults to the GITHUB_REPO env var if not provided.

    Returns:
        Detailed repo info including stats, topics, and recent activity.
    """
    target = repo_name or DEFAULT_REPO
    if not target:
        return "Error: Provide repo_name as 'owner/repo' or set GITHUB_REPO in .env"

    try:
        g    = _get_client()
        repo = g.get_repo(target)

        topics   = ", ".join(repo.get_topics()) or "none"
        branches = repo.get_branches().totalCount
        releases = repo.get_releases().totalCount

        return (
            f"Repository: {repo.full_name}\n"
            f"Description: {repo.description or '(none)'}\n"
            f"URL: {repo.html_url}\n\n"
            f"Stats:\n"
            f"  Stars:    {repo.stargazers_count:,}\n"
            f"  Forks:    {repo.forks_count:,}\n"
            f"  Watchers: {repo.watchers_count:,}\n"
            f"  Issues:   {repo.open_issues_count} open\n"
            f"  Branches: {branches}\n"
            f"  Releases: {releases}\n\n"
            f"Language:  {repo.language or 'N/A'}\n"
            f"Topics:    {topics}\n"
            f"License:   {repo.license.name if repo.license else 'None'}\n"
            f"Created:   {repo.created_at.strftime('%Y-%m-%d')}\n"
            f"Updated:   {repo.updated_at.strftime('%Y-%m-%d')}\n"
            f"Default branch: {repo.default_branch}\n"
        )

    except GithubException as e:
        if e.status == 404:
            return f"Repository '{target}' not found. Check the name format: owner/repo"
        return f"GitHub API error: {e.status} — {e.data.get('message', str(e))}"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


# ── Tool 3: list_issues ───────────────────────────────────────────────────────
@mcp.tool()
async def list_issues(
    repo_name: str = "",
    state: str = "open",
    label: str = "",
    max_results: int = 10,
) -> str:
    """List issues on a GitHub repository.

    Args:
        repo_name:   Full repo name 'owner/repo'. Defaults to GITHUB_REPO env var.
        state:       'open', 'closed', or 'all' (default 'open').
        label:       Filter by label name (e.g. 'bug', 'enhancement'). Optional.
        max_results: Maximum number of issues to return (default 10).

    Returns:
        Formatted list of issues with number, title, labels, and creation date.
    """
    target = repo_name or DEFAULT_REPO
    if not target:
        return "Error: Provide repo_name or set GITHUB_REPO in .env"

    try:
        g      = _get_client()
        repo   = g.get_repo(target)
        kwargs = {"state": state}
        if label:
            kwargs["labels"] = [repo.get_label(label)]

        issues = list(repo.get_issues(**kwargs))[:max_results]

        if not issues:
            return f"No {state} issues found on {target}."

        lines = [f"{len(issues)} {state} issues on {target}:\n"]
        for issue in issues:
            labels = ", ".join(l.name for l in issue.labels) or "none"
            lines.append(
                f"#{issue.number} {issue.title}\n"
                f"  Labels: {labels}  |  "
                f"Created: {issue.created_at.strftime('%Y-%m-%d')}  |  "
                f"URL: {issue.html_url}\n"
            )
        return "\n".join(lines)

    except GithubException as e:
        return f"GitHub API error: {e.status} — {e.data.get('message', str(e))}"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


# ── Tool 4: create_issue ──────────────────────────────────────────────────────
@mcp.tool()
async def create_issue(
    title: str,
    body: str = "",
    labels: str = "",
    repo_name: str = "",
) -> str:
    """Create a new issue on a GitHub repository.

    Args:
        title:     Issue title (required).
        body:      Issue description in Markdown (optional).
        labels:    Comma-separated label names (e.g. 'bug,help wanted'). Optional.
        repo_name: Full repo name 'owner/repo'. Defaults to GITHUB_REPO env var.

    Returns:
        URL and number of the created issue, or an error message.
    """
    target = repo_name or DEFAULT_REPO
    if not target:
        return "Error: Provide repo_name or set GITHUB_REPO in .env"
    if not title.strip():
        return "Error: Issue title cannot be empty."

    try:
        g    = _get_client()
        repo = g.get_repo(target)

        kwargs: dict = {"title": title.strip()}
        if body:
            kwargs["body"] = body
        if labels:
            label_names = [l.strip() for l in labels.split(",") if l.strip()]
            kwargs["labels"] = [repo.get_label(name) for name in label_names]

        issue = repo.create_issue(**kwargs)
        return (
            f"✅ Issue created successfully!\n"
            f"  Number: #{issue.number}\n"
            f"  Title:  {issue.title}\n"
            f"  URL:    {issue.html_url}\n"
        )

    except GithubException as e:
        if e.status == 422:
            return f"Validation error: {e.data.get('errors', e.data.get('message', str(e)))}"
        return f"GitHub API error: {e.status} — {e.data.get('message', str(e))}"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


# ── Tool 5: search_code ───────────────────────────────────────────────────────
@mcp.tool()
async def search_code(
    query: str,
    repo_name: str = "",
    language: str = "",
    max_results: int = 5,
) -> str:
    """Search for code across GitHub repositories.

    Args:
        query:       The search query (e.g. 'FastMCP tool decorator').
        repo_name:   Restrict search to this repo ('owner/repo'). Optional.
        language:    Filter by language (e.g. 'python'). Optional.
        max_results: Maximum number of results (default 5).

    Returns:
        List of matching files with repo, path, and a text snippet.
    """
    if not query.strip():
        return "Error: Search query cannot be empty."

    try:
        g = _get_client()

        full_query = query
        if repo_name or DEFAULT_REPO:
            full_query += f" repo:{repo_name or DEFAULT_REPO}"
        if language:
            full_query += f" language:{language}"

        results = list(g.search_code(full_query))[:max_results]

        if not results:
            return f"No code results found for: {query}"

        lines = [f"Top {len(results)} code results for '{query}':\n"]
        for r in results:
            lines.append(
                f"• {r.repository.full_name} / {r.path}\n"
                f"  URL: {r.html_url}\n"
            )
        return "\n".join(lines)

    except GithubException as e:
        if e.status == 403:
            return "Rate limit hit for code search. Wait 60 seconds and retry."
        return f"GitHub API error: {e.status} — {e.data.get('message', str(e))}"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


# ── Resource: GitHub profile ──────────────────────────────────────────────────
@mcp.resource("github://profile")
async def get_profile() -> str:
    """Your GitHub profile summary."""
    try:
        g    = _get_client()
        user = g.get_user()
        repos = list(user.get_repos())
        total_stars = sum(r.stargazers_count for r in repos)

        return (
            f"# GitHub Profile: {user.login}\n\n"
            f"Name:       {user.name or 'N/A'}\n"
            f"Bio:        {user.bio or 'N/A'}\n"
            f"Company:    {user.company or 'N/A'}\n"
            f"Location:   {user.location or 'N/A'}\n"
            f"URL:        {user.html_url}\n\n"
            f"Stats:\n"
            f"  Public repos:  {user.public_repos}\n"
            f"  Followers:     {user.followers}\n"
            f"  Following:     {user.following}\n"
            f"  Total stars:   {total_stars:,}\n"
            f"  Member since:  {user.created_at.strftime('%B %Y')}\n"
        )
    except Exception as e:
        return f"Could not load profile: {e}\nCheck that GITHUB_TOKEN is set in .env"


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("⚠️  GITHUB_TOKEN not set in .env — GitHub tools will return errors.")
        print("   Get a token: github.com/settings/tokens\n")
    else:
        print(f"✅ GitHub token loaded")
        print(f"   Default repo: {DEFAULT_REPO or '(not set — pass repo_name to each tool)'}\n")

    print("Starting GitHub MCP Server...")
    print("Test with: mcp dev github_mcp_server.py\n")
    mcp.run(transport="stdio")

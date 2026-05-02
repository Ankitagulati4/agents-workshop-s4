"""
HOMEWORK 3 — LangChain Custom Toolkit + LangGraph Agent
========================================================
Build a GitHubToolkit class grouping 3+ related tools,
then wire it into a LangGraph ReAct agent.

This demonstrates:
  - BaseTool subclassing for full tool control
  - BaseToolkit pattern for grouping related tools
  - Wiring a custom toolkit into a LangGraph stateful agent
  - Using different tool classes from the same toolkit

Run:
    python solution.py
"""

import os
import json
from typing import Type, Optional
from dotenv import load_dotenv
load_dotenv(override=True)

from langchain_core.tools import BaseTool, StructuredTool
from langchain_core.tools import BaseToolkit
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

MODEL = os.getenv("OPENAI_MODEL_NAME", "llama-3.3-70b-versatile")
llm   = ChatGroq(model=MODEL, temperature=0)

# ── Pydantic input schemas ────────────────────────────────────────────────────
class RepoInput(BaseModel):
    repo_name: str = Field(description="Full repo name as 'owner/repo', e.g. 'langchain-ai/langchain'")

class IssueInput(BaseModel):
    repo_name: str = Field(description="Full repo name as 'owner/repo'")
    title:     str = Field(description="Issue title")
    body:      str = Field(default="", description="Issue body in Markdown. Optional.")
    labels:    str = Field(default="", description="Comma-separated label names. Optional.")

class ListPRsInput(BaseModel):
    repo_name: str = Field(description="Full repo name as 'owner/repo'")
    state:     str = Field(default="open", description="PR state: 'open', 'closed', or 'all'")
    max_results: int = Field(default=5, description="Maximum number of PRs to return (1–20)")

class SearchInput(BaseModel):
    query:     str = Field(description="Search query string")
    repo_name: str = Field(default="", description="Restrict to this repo. Optional.")


# ── Individual tool implementations ───────────────────────────────────────────
# Using mock data so no GitHub token is required for the homework
# Replace _mock_* functions with real PyGithub calls if you have a GITHUB_TOKEN

MOCK_REPOS = {
    "alice/web-app": {
        "description": "A React + FastAPI web application",
        "language": "Python", "stars": 42, "forks": 8,
        "open_issues": 5, "default_branch": "main",
    },
    "alice/ml-toolkit": {
        "description": "Machine learning utilities and pipelines",
        "language": "Python", "stars": 128, "forks": 31,
        "open_issues": 12, "default_branch": "main",
    },
}

MOCK_ISSUES = {
    "alice/web-app": [
        {"number": 23, "title": "Login page crashes on mobile", "labels": ["bug", "mobile"], "state": "open"},
        {"number": 22, "title": "Add dark mode support", "labels": ["enhancement"], "state": "open"},
        {"number": 21, "title": "API rate limiting not working", "labels": ["bug", "backend"], "state": "open"},
    ],
    "alice/ml-toolkit": [
        {"number": 45, "title": "Pipeline fails on empty DataFrames", "labels": ["bug"], "state": "open"},
        {"number": 44, "title": "Add support for XGBoost models", "labels": ["enhancement"], "state": "open"},
    ],
}

MOCK_PRS = {
    "alice/web-app": [
        {"number": 31, "title": "Fix: mobile login crash", "state": "open", "author": "bob"},
        {"number": 30, "title": "Add dark mode toggle", "state": "open", "author": "carol"},
    ],
    "alice/ml-toolkit": [
        {"number": 62, "title": "Add XGBoost integration", "state": "open", "author": "dave"},
    ],
}

created_issues = []  # Track issues created during the session


# ── Tool classes (BaseTool subclass style) ─────────────────────────────────────
class GetRepoInfoTool(BaseTool):
    name:        str = "get_repo_info"
    description: str = (
        "Get detailed information about a GitHub repository including stats, "
        "language, open issues count, and description. "
        "Use when the user asks about a specific repo."
    )
    args_schema: Type[BaseModel] = RepoInput

    def _run(self, repo_name: str) -> str:
        token = os.getenv("GITHUB_TOKEN")
        if token:
            # Real implementation using PyGithub
            try:
                from github import Github
                g    = Github(token)
                repo = g.get_repo(repo_name)
                return (
                    f"Repo: {repo.full_name}\n"
                    f"Description: {repo.description}\n"
                    f"Language: {repo.language} | Stars: {repo.stargazers_count} | "
                    f"Forks: {repo.forks_count} | Open issues: {repo.open_issues_count}"
                )
            except Exception as e:
                return f"GitHub API error: {e}"

        # Mock fallback
        data = MOCK_REPOS.get(repo_name)
        if not data:
            return f"Repo '{repo_name}' not found. Available: {', '.join(MOCK_REPOS)}"
        return (
            f"Repo: {repo_name}\n"
            f"Description: {data['description']}\n"
            f"Language: {data['language']} | Stars: {data['stars']} | "
            f"Forks: {data['forks']} | Open issues: {data['open_issues']}"
        )

    async def _arun(self, repo_name: str) -> str:
        return self._run(repo_name)


class ListIssuesTool(BaseTool):
    name:        str = "list_issues"
    description: str = (
        "List open issues on a GitHub repository. "
        "Use when the user wants to see what issues exist, what bugs are reported, "
        "or what features are requested."
    )
    args_schema: Type[BaseModel] = RepoInput

    def _run(self, repo_name: str) -> str:
        token = os.getenv("GITHUB_TOKEN")
        if token:
            try:
                from github import Github
                g      = Github(token)
                repo   = g.get_repo(repo_name)
                issues = list(repo.get_issues(state="open"))[:10]
                if not issues:
                    return f"No open issues on {repo_name}"
                lines = [f"Open issues on {repo_name}:"]
                for i in issues:
                    labels = ", ".join(l.name for l in i.labels) or "none"
                    lines.append(f"  #{i.number} {i.title} (labels: {labels})")
                return "\n".join(lines)
            except Exception as e:
                return f"GitHub API error: {e}"

        # Mock fallback
        issues = MOCK_ISSUES.get(repo_name, []) + [
            {"number": i["number"], "title": i["title"],
             "labels": i["labels"], "state": "open"}
            for i in created_issues if i.get("repo") == repo_name
        ]
        if not issues:
            return f"No issues found for '{repo_name}'. Available: {', '.join(MOCK_ISSUES)}"
        lines = [f"Open issues on {repo_name}:"]
        for i in issues:
            lines.append(f"  #{i['number']} {i['title']} (labels: {', '.join(i['labels'])})")
        return "\n".join(lines)

    async def _arun(self, repo_name: str) -> str:
        return self._run(repo_name)


class CreateIssueTool(BaseTool):
    name:        str = "create_issue"
    description: str = (
        "Create a new issue on a GitHub repository. "
        "Use when the user explicitly asks to create, open, or file an issue."
    )
    args_schema: Type[BaseModel] = IssueInput

    def _run(self, repo_name: str, title: str, body: str = "", labels: str = "") -> str:
        token = os.getenv("GITHUB_TOKEN")
        if token:
            try:
                from github import Github
                g      = Github(token)
                repo   = g.get_repo(repo_name)
                kwargs: dict = {"title": title}
                if body:
                    kwargs["body"] = body
                if labels:
                    kwargs["labels"] = [repo.get_label(l.strip()) for l in labels.split(",")]
                issue = repo.create_issue(**kwargs)
                return f"✅ Issue #{issue.number} created: {issue.html_url}"
            except Exception as e:
                return f"GitHub API error: {e}"

        # Mock
        issue_num = 100 + len(created_issues) + 1
        label_list = [l.strip() for l in labels.split(",") if l.strip()]
        created_issues.append({
            "repo": repo_name, "number": issue_num,
            "title": title, "labels": label_list,
        })
        return f"✅ [MOCK] Issue #{issue_num} created on {repo_name}: '{title}'"

    async def _arun(self, repo_name: str, title: str, body: str = "", labels: str = "") -> str:
        return self._run(repo_name, title, body, labels)


class ListPRsTool(BaseTool):
    name:        str = "list_pull_requests"
    description: str = (
        "List pull requests on a GitHub repository. "
        "Use when the user asks about PRs, pending reviews, or code changes."
    )
    args_schema: Type[BaseModel] = ListPRsInput

    def _run(self, repo_name: str, state: str = "open", max_results: int = 5) -> str:
        token = os.getenv("GITHUB_TOKEN")
        if token:
            try:
                from github import Github
                g    = Github(token)
                repo = g.get_repo(repo_name)
                prs  = list(repo.get_pulls(state=state))[:max_results]
                if not prs:
                    return f"No {state} PRs on {repo_name}"
                lines = [f"{state.capitalize()} PRs on {repo_name}:"]
                for pr in prs:
                    lines.append(f"  #{pr.number} {pr.title} by @{pr.user.login}")
                return "\n".join(lines)
            except Exception as e:
                return f"GitHub API error: {e}"

        # Mock
        prs = MOCK_PRS.get(repo_name, [])
        if not prs:
            return f"No {state} PRs for '{repo_name}'. Available: {', '.join(MOCK_PRS)}"
        lines = [f"{state.capitalize()} PRs on {repo_name}:"]
        for pr in prs:
            lines.append(f"  #{pr['number']} {pr['title']} by @{pr['author']}")
        return "\n".join(lines)

    async def _arun(self, repo_name: str, state: str = "open", max_results: int = 5) -> str:
        return self._run(repo_name, state, max_results)


# ── Toolkit class ─────────────────────────────────────────────────────────────
class GitHubToolkit(BaseToolkit):
    """A toolkit grouping all GitHub-related tools for use in an agent."""

    def get_tools(self) -> list[BaseTool]:
        """Return all tools in this toolkit."""
        return [
            GetRepoInfoTool(),
            ListIssuesTool(),
            CreateIssueTool(),
            ListPRsTool(),
        ]

    @classmethod
    def from_env(cls) -> "GitHubToolkit":
        """Create a toolkit, logging whether real or mock mode will be used."""
        token = os.getenv("GITHUB_TOKEN")
        if token:
            print("✅ GITHUB_TOKEN found — tools will use real GitHub API")
        else:
            print("⚠️  GITHUB_TOKEN not set — tools will use mock data")
            print("   Set GITHUB_TOKEN in .env for real GitHub access\n")
        return cls()


# ── LangGraph agent wiring ────────────────────────────────────────────────────
def build_github_agent():
    """Wire the GitHubToolkit into a LangGraph ReAct agent with memory."""
    toolkit  = GitHubToolkit.from_env()
    tools    = toolkit.get_tools()

    print(f"Loaded {len(tools)} tools from GitHubToolkit:")
    for t in tools:
        print(f"  • {t.name}: {t.description[:60]}...")
    print()

    checkpointer = MemorySaver()
    agent_app    = create_react_agent(llm, tools, checkpointer=checkpointer)
    return agent_app


# ── Test queries ──────────────────────────────────────────────────────────────
DEMO_QUERIES = [
    "What can you tell me about the alice/web-app repository?",
    "List all open issues on alice/web-app",
    "What PRs are open on alice/ml-toolkit?",
    "Create an issue on alice/web-app titled 'Add loading spinner to API calls' with label 'enhancement'",
    "Now show me all issues on alice/web-app to confirm it was created",
]


def run():
    agent_app = build_github_agent()
    config    = {"configurable": {"thread_id": "hw3-github"}}

    print("="*62)
    print("GitHub Toolkit Agent — LangGraph + Custom Toolkit")
    print(f"Model: {MODEL}")
    print("="*62)

    for i, query in enumerate(DEMO_QUERIES, 1):
        print(f"\n{'─'*62}")
        print(f"Query {i}: {query}")
        print('─'*62)

        result = agent_app.invoke(
            {"messages": [HumanMessage(content=query)]},
            config,
        )
        final_msg = result["messages"][-1].content
        print(f"\n✅ Answer: {final_msg[:400]}{'...' if len(final_msg) > 400 else ''}")

    print(f"\n{'='*62}")
    print("💡 Key learnings:")
    print("  1. BaseTool subclass gives you full control over tool behaviour")
    print("  2. BaseToolkit groups related tools — easy to add/remove as a set")
    print("  3. MemorySaver means the agent remembers previous queries")
    print("  4. create_react_agent wires tools and LLM in one line")
    print("  5. Same toolkit works with LangGraph, LangChain AgentExecutor, etc.")


if __name__ == "__main__":
    run()

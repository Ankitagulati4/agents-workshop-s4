"""
verify_setup.py — Session 4 Pre-Workshop Check
Run this before the session to confirm your environment is ready.

    python verify_setup.py
"""
import sys, os

PASS, FAIL, WARN = "✅", "❌", "⚠️ "
SEP = "─" * 62

def check(label, fn):
    try:
        msg = fn()
        print(f"  {PASS}  {label}: {msg or 'OK'}")
        return True
    except Exception as e:
        print(f"  {FAIL}  {label}: {e}")
        return False

failures = []

# ── 1. Python ─────────────────────────────────────────────────────────────────
print(f"\n{SEP}\n  PYTHON\n{SEP}")
v = sys.version_info
if v >= (3, 10):
    print(f"  {PASS}  Python {v.major}.{v.minor}.{v.micro}")
else:
    print(f"  {FAIL}  Python {v.major}.{v.minor} — need 3.10+")
    failures.append("Python version")

# ── 2. Package imports ────────────────────────────────────────────────────────
print(f"\n{SEP}\n  PACKAGES\n{SEP}")
pkgs = [
    ("openai",             "openai"),
    ("langchain",          "langchain"),
    ("langchain_openai",   "langchain-openai"),
    ("langchain_community","langchain-community"),
    ("langgraph",          "langgraph"),
    ("mcp",                "mcp[cli]"),
    ("fastapi",            "fastapi"),
    ("uvicorn",            "uvicorn"),
    ("httpx",              "httpx"),
    ("pydantic",           "pydantic"),
    ("dotenv",             "python-dotenv"),
]
for mod, pip in pkgs:
    ok = check(pip, lambda m=mod: __import__(m) and "imported")
    if not ok:
        failures.append(pip)

# ── 3. Environment ────────────────────────────────────────────────────────────
print(f"\n{SEP}\n  ENVIRONMENT / API KEYS\n{SEP}")
try:
    from dotenv import load_dotenv
    if os.path.exists(".env"):
        load_dotenv(override=True)
        print(f"  {PASS}  .env loaded")
    else:
        print(f"  {WARN}  .env not found — run: cp .env.example .env")
except Exception as e:
    print(f"  {FAIL}  dotenv: {e}")

openai_key = os.getenv("OPENAI_API_KEY", "")
groq_key   = os.getenv("GROQ_API_KEY", "")

if openai_key.startswith("sk-"):
    print(f"  {PASS}  OPENAI_API_KEY set")
elif groq_key.startswith("gsk_"):
    print(f"  {PASS}  GROQ_API_KEY set (using Groq instead of OpenAI)")
else:
    print(f"  {FAIL}  No valid LLM key — set OPENAI_API_KEY or GROQ_API_KEY")
    failures.append("LLM API key")

for opt_key, label in [("TAVILY_API_KEY", "Tavily search"), ("GITHUB_TOKEN", "GitHub MCP (homework)")]:
    val = os.getenv(opt_key, "")
    if val:
        print(f"  {PASS}  {opt_key} set ({label})")
    else:
        print(f"  {WARN}  {opt_key} not set — optional ({label})")

# ── 4. LLM smoke test ─────────────────────────────────────────────────────────
print(f"\n{SEP}\n  LLM SMOKE TEST (1 real API call)\n{SEP}")

def openai_test():
    from openai import OpenAI
    r = OpenAI().chat.completions.create(
        model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini"),
        messages=[{"role": "user", "content": "Reply: SETUP_OK"}],
        max_tokens=10,
    )
    ans = r.choices[0].message.content.strip()
    assert "SETUP_OK" in ans, f"Got: {ans}"
    return f"model replied '{ans}'"

def groq_test():
    from langchain_groq import ChatGroq
    llm = ChatGroq(
        model=os.getenv("OPENAI_MODEL_NAME", "llama-3.3-70b-versatile"),
        temperature=0,
    )
    ans = llm.invoke("Reply with exactly: SETUP_OK").content.strip()
    assert "SETUP_OK" in ans, f"Got: {ans}"
    return f"model replied '{ans}'"

if groq_key.startswith("gsk_"):
    ok = check("Groq API", groq_test)
    if not ok: failures.append("Groq API")
elif openai_key.startswith("sk-"):
    ok = check("OpenAI API", openai_test)
    if not ok: failures.append("OpenAI API")
else:
    print(f"  {WARN}  Skipped — no valid API key")

# ── 5. Framework checks ───────────────────────────────────────────────────────
print(f"\n{SEP}\n  FRAMEWORK QUICK CHECKS\n{SEP}")

def lc_tools_check():
    from langchain_core.tools import tool
    @tool
    def hello(name: str) -> str:
        """Say hello."""
        return f"Hello {name}"
    assert hello.name == "hello"
    return f"@tool decorator works, tool name='{hello.name}'"

def mcp_check():
    from mcp.server.fastmcp import FastMCP
    s = FastMCP("test")
    try:
        from importlib.metadata import version
        v = version("mcp")
    except Exception:
        v = "unknown"
    return f"FastMCP instantiated OK (v{v})"

def fastapi_check():
    from fastapi import FastAPI
    app = FastAPI()
    return "FastAPI importable"

def httpx_check():
    import httpx
    return f"httpx {httpx.__version__}"

for label, fn in [
    ("LangChain @tool", lc_tools_check),
    ("MCP FastMCP",     mcp_check),
    ("FastAPI",         fastapi_check),
    ("httpx",           httpx_check),
]:
    ok = check(label, fn)
    if not ok: failures.append(label)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{SEP}\n  SUMMARY\n{SEP}")
if not failures:
    print(f"""
  {PASS}  ALL CHECKS PASSED — you're ready for Session 4!
  Post a ✅ in the workshop group chat.
""")
else:
    print(f"""
  {FAIL}  {len(failures)} check(s) failed: {', '.join(failures)}
  Fix: pip install -r requirements.txt
       cp .env.example .env  (then add OPENAI_API_KEY)
""")

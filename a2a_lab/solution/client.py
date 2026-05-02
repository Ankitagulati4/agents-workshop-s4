"""
LAB 3 SOLUTION — A2A Client with 2-Agent Routing
=================================================
Demonstrates:
  1. Agent discovery (fetch Agent Card)
  2. Skill-based task routing
  3. Chaining: output of Agent A → input of Agent B

Run TWO servers first:
    Terminal 1: uvicorn solution.server:app --reload --port 8001
    Terminal 2: uvicorn solution.server:app --reload --port 8002

Then:
    python solution/client.py
"""

import httpx
import uuid
import json

AGENT_A_URL = "http://localhost:8001"  # Research & Explanation Agent
AGENT_B_URL = "http://localhost:8002"  # Same server, different instance


# ── A2A helpers ───────────────────────────────────────────────────────────────
def discover(base_url: str) -> dict:
    r = httpx.get(f"{base_url}/.well-known/agent.json", timeout=5)
    r.raise_for_status()
    return r.json()


def send_task(base_url: str, text: str, skill_id: str = None, task_id: str = None) -> dict:
    payload = {
        "id":      task_id or str(uuid.uuid4())[:8],
        "message": {"role": "user", "parts": [{"text": text}]},
    }
    if skill_id:
        payload["skillId"] = skill_id

    r = httpx.post(f"{base_url}/tasks/send", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def check_skill_match(card: dict, text: str) -> str | None:
    """Simple keyword-based skill routing — in production use LLM-based routing."""
    text_lower = text.lower()
    for skill in card.get("skills", []):
        sid = skill["id"]
        if sid == "compare" and any(w in text_lower for w in ["compare", "vs", "versus", "difference"]):
            return "compare"
        if sid == "summarise" and any(w in text_lower for w in ["summarise", "summary", "brief", "tldr"]):
            return "summarise"
    return "explain"  # default


# ── Main demo ─────────────────────────────────────────────────────────────────
def demo_basic(agent_url: str, card: dict):
    """Send 3 tasks to one agent, using skill routing."""
    print(f"\n{'─'*62}")
    print(f"Demo 1: Basic task routing → {card['name']}")
    print('─'*62)

    queries = [
        "What is MCP and why was it created?",
        "Compare LangGraph vs CrewAI for production use",
        "Summarise the A2A protocol in key points",
    ]

    for q in queries:
        skill = check_skill_match(card, q)
        print(f"\n  Query:  {q}")
        print(f"  Skill:  {skill}")
        resp = send_task(agent_url, q, skill_id=skill)
        print(f"  Status: {resp['status']}")
        if resp.get("result"):
            lines = resp["result"].strip().split("\n")
            preview = "\n  ".join(lines[:4])
            print(f"  Result:\n  {preview}")
            if len(lines) > 4:
                print(f"  ... [{len(lines)-4} more lines]")


def demo_chained(agent_a_url: str, agent_b_url: str, card_a: dict, card_b: dict):
    """
    Chained A2A:
      Agent A (explain) → summarise output → Agent B (reformat as bullet points)
    """
    print(f"\n{'─'*62}")
    print("Demo 2: Chained A2A — Agent A explains → Agent B re-formats")
    print('─'*62)

    topic = "How the LangGraph StateGraph works"
    print(f"\n  Topic: {topic}")

    # Step 1: Agent A explains
    print(f"\n  [Step 1] Sending to Agent A ({card_a['name']})...")
    resp_a = send_task(agent_a_url, topic, skill_id="explain", task_id="chain-step1")
    explanation = resp_a.get("result", "")
    print(f"  Status: {resp_a['status']} ({len(explanation)} chars)")

    if not explanation:
        print("  ❌ Agent A returned no result — stopping chain")
        return

    # Step 2: Agent B summarises the explanation
    print(f"\n  [Step 2] Sending Agent A's output to Agent B ({card_b['name']})...")
    prompt_b = f"Summarise the following explanation into exactly 5 bullet points:\n\n{explanation}"
    resp_b = send_task(agent_b_url, prompt_b, skill_id="summarise", task_id="chain-step2")

    print(f"  Status: {resp_b['status']}")
    print(f"\n  ✅ Final chained result (Agent B summary):")
    print("  " + "─"*50)
    for line in (resp_b.get("result") or "").strip().split("\n"):
        print(f"  {line}")


def demo_routing_decision(agent_a_url: str, agent_b_url: str, card_a: dict, card_b: dict):
    """
    Routing demo: orchestrator decides which agent to send each task to.
    """
    print(f"\n{'─'*62}")
    print("Demo 3: Orchestrator routing — pick the right agent per task")
    print('─'*62)

    tasks = [
        "What is the difference between MCP tools and resources?",
        "Give me a 5-bullet summary of what LangChain is",
        "Explain what an Agent Card is in the A2A protocol",
    ]

    for task_text in tasks:
        # Simple routing rule: summarise tasks go to Agent B, rest to Agent A
        if "summary" in task_text.lower() or "summarise" in task_text.lower():
            target_url  = agent_b_url
            target_name = card_b["name"]
            skill       = "summarise"
        else:
            target_url  = agent_a_url
            target_name = card_a["name"]
            skill       = check_skill_match(card_a, task_text)

        print(f"\n  Task:   {task_text}")
        print(f"  Routed → {target_name} (skill: {skill})")

        resp = send_task(target_url, task_text, skill_id=skill)
        result_preview = (resp.get("result") or "")[:150]
        print(f"  Status: {resp['status']}")
        print(f"  Result: {result_preview}{'...' if len(resp.get('result',''))>150 else ''}")


def main():
    print("="*62)
    print("A2A Client — Agent Discovery & Task Routing")
    print("="*62)

    # ── Discover both agents ──────────────────────────────────────────────────
    print(f"\nDiscovering agents...")
    errors = []

    try:
        card_a = discover(AGENT_A_URL)
        print(f"  ✅ Agent A: {card_a['name']} at {AGENT_A_URL}")
        print(f"     Skills: {[s['id'] for s in card_a.get('skills',[])]}")
    except Exception as e:
        print(f"  ❌ Agent A unreachable at {AGENT_A_URL}: {e}")
        errors.append("A")
        card_a = {}

    try:
        card_b = discover(AGENT_B_URL)
        print(f"  ✅ Agent B: {card_b['name']} at {AGENT_B_URL}")
        print(f"     Skills: {[s['id'] for s in card_b.get('skills',[])]}")
    except Exception as e:
        print(f"  ⚠️  Agent B unreachable at {AGENT_B_URL}: {e}")
        print(f"     (Run: uvicorn solution.server:app --reload --port 8002)")
        card_b = card_a  # fallback: use same agent
        AGENT_B_URL_EFFECTIVE = AGENT_A_URL
        errors.append("B")

    AGENT_B_URL_EFFECTIVE = AGENT_B_URL if "B" not in errors else AGENT_A_URL

    if "A" in errors:
        print("\n❌ Cannot continue — start Agent A first:")
        print("   uvicorn solution.server:app --reload --port 8001")
        return

    # ── Run demos ─────────────────────────────────────────────────────────────
    demo_basic(AGENT_A_URL, card_a)
    demo_chained(AGENT_A_URL, AGENT_B_URL_EFFECTIVE, card_a, card_b)
    demo_routing_decision(AGENT_A_URL, AGENT_B_URL_EFFECTIVE, card_a, card_b)

    print(f"\n{'='*62}")
    print("✅ All demos complete!")
    print("\n💡 Reflection questions:")
    print("  1. How is this different from just calling an LLM directly?")
    print("  2. What would you add to the Agent Card for production?")
    print("  3. How would you handle Agent B being temporarily unavailable?")
    print("  4. What's the benefit of the task lifecycle (submitted→working→completed)?")


if __name__ == "__main__":
    main()

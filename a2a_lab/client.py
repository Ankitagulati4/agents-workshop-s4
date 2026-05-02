"""
LAB 3 — A2A Client
==================
This client:
  1. Fetches the Agent Card from the running server
  2. Prints the agent's capabilities
  3. Sends tasks and prints responses

Run AFTER starting the server:
    Terminal 1:  uvicorn starter:app --reload --port 8001
    Terminal 2:  python client.py
"""

import httpx
import uuid
import json

AGENT_URL = "http://localhost:8001"


def discover_agent(base_url: str) -> dict:
    """Fetch and return the agent card."""
    r = httpx.get(f"{base_url}/.well-known/agent.json", timeout=5)
    r.raise_for_status()
    return r.json()


def send_task(base_url: str, text: str, skill_id: str = None) -> dict:
    """Send a task to the agent and return the response."""
    task_id = str(uuid.uuid4())[:8]
    payload = {
        "id": task_id,
        "message": {
            "role": "user",
            "parts": [{"text": text}]
        },
    }
    if skill_id:
        payload["skillId"] = skill_id

    r = httpx.post(f"{base_url}/tasks/send", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def poll_task(base_url: str, task_id: str) -> dict:
    """Poll a task by ID."""
    r = httpx.get(f"{base_url}/tasks/{task_id}", timeout=5)
    r.raise_for_status()
    return r.json()


def main():
    print("="*62)
    print("A2A Client — Discovering and delegating to remote agent")
    print("="*62)

    # 1. Discover
    print(f"\n[1] Fetching Agent Card from {AGENT_URL}/.well-known/agent.json")
    try:
        card = discover_agent(AGENT_URL)
    except Exception as e:
        print(f"❌ Cannot reach agent at {AGENT_URL}")
        print(f"   Make sure the server is running:")
        print(f"   uvicorn starter:app --reload --port 8001")
        return

    print(f"\n  Agent name:    {card.get('name', 'unknown')}")
    print(f"  Description:   {card.get('description', '')}")
    print(f"  Version:       {card.get('version', '')}")
    print(f"  Skills:")
    for skill in card.get("skills", []):
        print(f"    • {skill.get('id')}: {skill.get('name')} — {skill.get('description', '')}")

    # 2. Send tasks
    tasks_to_send = [
        "What are the 3 most important things to know about the MCP protocol?",
        "Explain the difference between MCP and A2A in 2 sentences.",
        "What is LangGraph and when should I use it?",
    ]

    skills = card.get("skills", [])
    skill_id = skills[0]["id"] if skills else None

    print(f"\n[2] Sending {len(tasks_to_send)} tasks to agent...")
    for i, text in enumerate(tasks_to_send, 1):
        print(f"\n  Task {i}: {text[:60]}...")
        try:
            response = send_task(AGENT_URL, text, skill_id=skill_id)
            status = response.get("status", "unknown")
            result = response.get("result", "")
            print(f"  Status: {status}")
            if result:
                # Truncate for display
                preview = result[:200] + ("..." if len(result) > 200 else "")
                print(f"  Result: {preview}")
            elif response.get("error"):
                print(f"  Error:  {response['error']}")
        except Exception as e:
            print(f"  ❌ Request failed: {e}")

    # 3. Interactive mode
    print(f"\n{'='*62}")
    print("Interactive mode — type your task (or 'quit' to exit)")
    print("="*62)

    while True:
        text = input("\n> ").strip()
        if text.lower() in ("quit", "exit", "q"):
            break
        if not text:
            continue
        try:
            response = send_task(AGENT_URL, text, skill_id=skill_id)
            print(f"\n✅ [{response.get('status')}] {response.get('result', response.get('error', ''))}")
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()

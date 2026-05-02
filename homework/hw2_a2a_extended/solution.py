"""
HOMEWORK 2 — Extended A2A: Full Task Lifecycle with 2-Agent System
==================================================================
Build a 2-agent A2A system where:
  - Agent A (Orchestrator): receives user tasks, classifies them,
    routes to the right specialist, tracks lifecycle
  - Agent B (Specialist):   handles specialist tasks (code review,
    data analysis, or technical writing)

Full task lifecycle implemented:
  submitted → working → completed
                      → failed
                      → input-required (asks user a clarifying question)

Run:
    # Terminal 1 — Specialist Agent (Agent B)
    uvicorn solution:specialist_app --port 8002 --reload

    # Terminal 2 — Orchestrator (Agent A) which routes to Agent B
    uvicorn solution:orchestrator_app --port 8001 --reload

    # Terminal 3 — Test client
    python solution.py --mode client
"""

import os
import uuid
import asyncio
import argparse
from typing import Optional
from dotenv import load_dotenv
load_dotenv(override=True)

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

MODEL = os.getenv("OPENAI_MODEL_NAME", "llama-3.3-70b-versatile")
llm   = ChatGroq(model=MODEL, temperature=0)

# ── Shared models ─────────────────────────────────────────────────────────────
class MessagePart(BaseModel):
    text: str

class Message(BaseModel):
    role:  str
    parts: list[MessagePart]

class TaskRequest(BaseModel):
    id:      str
    message: Message
    skillId: Optional[str] = None

class TaskResponse(BaseModel):
    id:                str
    status:            str   # submitted|working|input-required|completed|failed
    result:            Optional[str] = None
    error:             Optional[str] = None
    clarifying_question: Optional[str] = None   # set when status=input-required


# ════════════════════════════════════════════════════════════════════════════
# AGENT B — Specialist Agent (port 8002)
# ════════════════════════════════════════════════════════════════════════════

specialist_app = FastAPI(title="Specialist Agent B")
specialist_tasks: dict = {}

SPECIALIST_CARD = {
    "name":        "Specialist Agent",
    "description": "Handles code review, data analysis, and technical writing tasks.",
    "url":         f"http://localhost:{os.getenv('AGENT_B_PORT', '8002')}",
    "version":     "1.0.0",
    "skills": [
        {
            "id":          "code_review",
            "name":        "Code Review",
            "description": "Reviews Python code for bugs, style, and security issues.",
            "inputModes":  ["text"],
            "outputModes": ["text"],
        },
        {
            "id":          "data_analysis",
            "name":        "Data Analysis Guidance",
            "description": "Provides guidance on how to analyse a dataset or problem.",
            "inputModes":  ["text"],
            "outputModes": ["text"],
        },
        {
            "id":          "tech_writing",
            "name":        "Technical Writing",
            "description": "Writes technical documentation, READMEs, and explanations.",
            "inputModes":  ["text"],
            "outputModes": ["text"],
        },
    ],
}

SPECIALIST_PROMPTS = {
    "code_review": (
        "You are a senior code reviewer. Review the provided code for: "
        "(1) bugs and logic errors, (2) security vulnerabilities, "
        "(3) performance issues, (4) code style and readability. "
        "Format your review with clear sections and specific line references."
    ),
    "data_analysis": (
        "You are a data scientist. Provide clear, practical guidance on "
        "how to approach the described data analysis problem. "
        "Include: recommended approach, tools, potential pitfalls, and next steps."
    ),
    "tech_writing": (
        "You are a technical writer. Produce clear, well-structured technical "
        "documentation. Use proper Markdown formatting with headers, code blocks, "
        "and bullet points where appropriate."
    ),
}


@specialist_app.get("/.well-known/agent.json")
async def specialist_card():
    return SPECIALIST_CARD


@specialist_app.post("/tasks/send", response_model=TaskResponse)
async def specialist_send(request: TaskRequest):
    tid  = request.id or str(uuid.uuid4())[:8]
    text = " ".join(p.text for p in request.message.parts)
    specialist_tasks[tid] = {"status": "working", "result": None, "error": None}

    try:
        system_msg = SPECIALIST_PROMPTS.get(
            request.skillId,
            "You are a helpful technical specialist. Answer with precision and detail."
        )
        resp = llm.invoke([SystemMessage(content=system_msg), HumanMessage(content=text)])
        specialist_tasks[tid] = {"status": "completed", "result": resp.content, "error": None}
        return TaskResponse(id=tid, status="completed", result=resp.content)
    except Exception as e:
        specialist_tasks[tid] = {"status": "failed", "result": None, "error": str(e)}
        return TaskResponse(id=tid, status="failed", error=str(e))


@specialist_app.get("/tasks/{tid}", response_model=TaskResponse)
async def specialist_get(tid: str):
    if tid not in specialist_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    t = specialist_tasks[tid]
    return TaskResponse(id=tid, **t)


@specialist_app.get("/health")
async def specialist_health():
    return {"status": "ok", "agent": "Specialist Agent B"}


# ════════════════════════════════════════════════════════════════════════════
# AGENT A — Orchestrator (port 8001)
# Routes incoming tasks to Agent B after classifying them
# ════════════════════════════════════════════════════════════════════════════

orchestrator_app = FastAPI(title="Orchestrator Agent A")
orchestrator_tasks: dict = {}

SPECIALIST_B_URL = f"http://localhost:{os.getenv('AGENT_B_PORT', '8002')}"

ORCHESTRATOR_CARD = {
    "name":        "Orchestrator Agent",
    "description": (
        "Receives general user tasks, classifies them, and routes to "
        "the appropriate specialist agent. Handles the full task lifecycle."
    ),
    "url":     f"http://localhost:{os.getenv('AGENT_A_PORT', '8001')}",
    "version": "1.0.0",
    "skills":  [{"id": "general", "name": "General Task Router",
                 "description": "Accepts any task and routes it appropriately.",
                 "inputModes": ["text"], "outputModes": ["text"]}],
}

CLASSIFY_PROMPT = """Classify this user request into exactly one of these categories:
- code_review     (if they want code reviewed, analysed, or debugged)
- data_analysis   (if they want help with data, statistics, or analysis approach)
- tech_writing    (if they want documentation, README, or explanation written)
- general         (if it doesn't fit the above)
- needs_more_info (if the request is ambiguous and you need a clarifying question)

Respond with ONLY the category name, nothing else.
Request: {text}"""

CLARIFY_PROMPT = """The user sent an ambiguous request. Generate ONE short clarifying question
that would help you route it correctly.
Request: {text}
Question (one sentence only):"""


@orchestrator_app.get("/.well-known/agent.json")
async def orchestrator_card():
    return ORCHESTRATOR_CARD


@orchestrator_app.post("/tasks/send", response_model=TaskResponse)
async def orchestrator_send(request: TaskRequest):
    tid  = request.id or str(uuid.uuid4())[:8]
    text = " ".join(p.text for p in request.message.parts)

    # 1. submitted
    orchestrator_tasks[tid] = {
        "status": "submitted", "result": None,
        "error": None, "clarifying_question": None
    }

    # 2. working
    orchestrator_tasks[tid]["status"] = "working"

    try:
        # Classify
        category = llm.invoke([HumanMessage(
            content=CLASSIFY_PROMPT.format(text=text)
        )]).content.strip().lower()

        # input-required: ask a clarifying question
        if category == "needs_more_info":
            question = llm.invoke([HumanMessage(
                content=CLARIFY_PROMPT.format(text=text)
            )]).content.strip()

            orchestrator_tasks[tid].update({
                "status": "input-required",
                "clarifying_question": question,
            })
            return TaskResponse(
                id=tid, status="input-required",
                clarifying_question=question,
            )

        # General: handle locally without routing
        if category == "general":
            resp = llm.invoke([
                SystemMessage(content="You are a helpful AI assistant."),
                HumanMessage(content=text),
            ])
            orchestrator_tasks[tid].update({"status": "completed", "result": resp.content})
            return TaskResponse(id=tid, status="completed", result=resp.content)

        # Route to Specialist B
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{SPECIALIST_B_URL}/tasks/send",
                json={
                    "id":      f"{tid}-routed",
                    "message": {"role": "user", "parts": [{"text": text}]},
                    "skillId": category,
                }
            )
            r.raise_for_status()
            specialist_resp = r.json()

        final_result = (
            f"[Routed to Specialist Agent — skill: {category}]\n\n"
            + (specialist_resp.get("result") or specialist_resp.get("error", "No result"))
        )

        orchestrator_tasks[tid].update({"status": "completed", "result": final_result})
        return TaskResponse(id=tid, status="completed", result=final_result)

    except httpx.ConnectError:
        err = (
            f"Specialist Agent B unreachable at {SPECIALIST_B_URL}. "
            "Start it with: uvicorn solution:specialist_app --port 8002"
        )
        orchestrator_tasks[tid].update({"status": "failed", "error": err})
        return TaskResponse(id=tid, status="failed", error=err)

    except Exception as e:
        orchestrator_tasks[tid].update({"status": "failed", "error": str(e)})
        return TaskResponse(id=tid, status="failed", error=str(e))


@orchestrator_app.get("/tasks/{tid}", response_model=TaskResponse)
async def orchestrator_get(tid: str):
    if tid not in orchestrator_tasks:
        raise HTTPException(404, "Task not found")
    t = orchestrator_tasks[tid]
    return TaskResponse(id=tid, **t)


@orchestrator_app.get("/health")
async def orchestrator_health():
    return {"status": "ok", "agent": "Orchestrator Agent A"}


# ════════════════════════════════════════════════════════════════════════════
# CLIENT (run with: python solution.py --mode client)
# ════════════════════════════════════════════════════════════════════════════

async def run_client():
    BASE = "http://localhost:8001"

    print("="*62)
    print("A2A Extended Client — Full Lifecycle Demo")
    print("="*62)

    async with httpx.AsyncClient(timeout=30) as client:
        # Discover
        r = await client.get(f"{BASE}/.well-known/agent.json")
        card = r.json()
        print(f"\n✅ Discovered: {card['name']}")

        test_cases = [
            ("code_review",    "Please review this Python code:\ndef add(a, b):\n  return a+b\nprint(add(1,'2'))"),
            ("data_analysis",  "I have a CSV with customer churn data: user_id, tenure_days, plan, churned. How should I analyse it?"),
            ("tech_writing",   "Write a short README for an MCP server that provides GitHub tools."),
            ("ambiguous",      "Help me with my thing"),   # triggers input-required
            ("general",        "What is the capital of France?"),
        ]

        for label, task_text in test_cases:
            print(f"\n{'─'*62}")
            print(f"Test: {label}")
            print(f"Task: {task_text[:70]}...")

            r = await client.post(f"{BASE}/tasks/send", json={
                "id":      str(uuid.uuid4())[:8],
                "message": {"role": "user", "parts": [{"text": task_text}]},
            })
            resp = r.json()
            status = resp["status"]
            print(f"Status: {status}")

            if status == "input-required":
                print(f"Clarifying question: {resp.get('clarifying_question')}")
            elif status == "completed":
                result = resp.get("result", "")
                lines  = result.strip().split("\n")
                print("Result (first 4 lines):")
                for line in lines[:4]:
                    print(f"  {line}")
                if len(lines) > 4:
                    print(f"  ... [{len(lines)-4} more lines]")
            elif status == "failed":
                print(f"Error: {resp.get('error')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["client"], default="client")
    args = parser.parse_args()

    if args.mode == "client":
        print("Running A2A client demo...")
        print("Make sure both servers are running:")
        print("  uvicorn solution:specialist_app --port 8002")
        print("  uvicorn solution:orchestrator_app --port 8001\n")
        asyncio.run(run_client())
    else:
        print("Use --mode client to run the client demo.")
        print("To run servers, use uvicorn directly:")
        print("  uvicorn solution:specialist_app --port 8002")
        print("  uvicorn solution:orchestrator_app --port 8001")

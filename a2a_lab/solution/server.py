"""
LAB 3 SOLUTION — A2A Server
============================
Complete working A2A agent server.

Run:
    uvicorn solution.server:app --reload --port 8001

Then in another terminal:
    python solution/client.py
"""

import os, uuid
from typing import Optional
from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

MODEL = os.getenv("OPENAI_MODEL_NAME", "llama-3.3-70b-versatile")
llm   = ChatGroq(model=MODEL, temperature=0.3)

app   = FastAPI(title="A2A Research Agent", version="1.0.0")
tasks: dict = {}


# ── Agent Card ────────────────────────────────────────────────────────────────
agent_card = {
    "name":        "Research & Explanation Agent",
    "description": (
        "A specialist agent that answers technical questions about AI frameworks, "
        "protocols, and engineering concepts. Provides clear, structured explanations."
    ),
    "url":         f"http://localhost:{os.getenv('AGENT_A_PORT', '8001')}",
    "version":     "1.0.0",
    "defaultInputModes":  ["text"],
    "defaultOutputModes": ["text"],
    "skills": [
        {
            "id":          "explain",
            "name":        "Explain a Concept",
            "description": "Explains a technical AI/engineering concept clearly with examples.",
            "inputModes":  ["text"],
            "outputModes": ["text"],
            "examples":    ["What is LangGraph?", "Explain the MCP protocol."],
        },
        {
            "id":          "compare",
            "name":        "Compare Technologies",
            "description": "Compares two or more technologies with a structured analysis.",
            "inputModes":  ["text"],
            "outputModes": ["text"],
            "examples":    ["Compare MCP and A2A", "LangGraph vs CrewAI"],
        },
        {
            "id":          "summarise",
            "name":        "Summarise a Topic",
            "description": "Provides a concise 3–5 bullet point summary of any topic.",
            "inputModes":  ["text"],
            "outputModes": ["text"],
        },
    ],
    "capabilities": {
        "streaming":             False,
        "pushNotifications":     False,
        "stateTransitionHistory": True,
    },
}


# ── Pydantic models ───────────────────────────────────────────────────────────
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
    id:     str
    status: str                  # submitted | working | completed | failed
    result: Optional[str] = None
    error:  Optional[str] = None


# ── Skill → system prompt mapping ────────────────────────────────────────────
SKILL_PROMPTS = {
    "explain": (
        "You are a technical educator. Explain the concept clearly and concisely. "
        "Include: a 1-sentence definition, the key idea, a simple analogy, and one code example if relevant."
    ),
    "compare": (
        "You are a senior engineer. Compare the technologies objectively. "
        "Structure: brief intro, comparison table (3–5 dimensions), when to use each, verdict."
    ),
    "summarise": (
        "You are a research analyst. Summarise the topic in exactly 5 bullet points. "
        "Each bullet: one specific, concrete fact. No fluff."
    ),
    None: (
        "You are a helpful AI assistant specialising in AI engineering and software development. "
        "Answer accurately and concisely."
    ),
}


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/.well-known/agent.json")
async def get_agent_card():
    """A2A discovery endpoint — returns this agent's capabilities."""
    return agent_card


@app.post("/tasks/send", response_model=TaskResponse)
async def send_task(request: TaskRequest):
    """Accept a task, process it, and return the result."""
    task_id = request.id or str(uuid.uuid4())[:8]

    # Store initial state
    tasks[task_id] = {"status": "submitted", "result": None, "error": None}

    # Extract user text
    text = " ".join(part.text for part in request.message.parts)

    # Update to working
    tasks[task_id]["status"] = "working"

    try:
        system_prompt = SKILL_PROMPTS.get(request.skillId, SKILL_PROMPTS[None])
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=text),
        ])
        result = response.content
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = result

        return TaskResponse(id=task_id, status="completed", result=result)

    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"]  = str(e)
        return TaskResponse(id=task_id, status="failed", error=str(e))


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Poll a task by ID."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    t = tasks[task_id]
    return TaskResponse(id=task_id, **t)


@app.get("/health")
async def health():
    return {"status": "ok", "agent": agent_card["name"], "model": MODEL}

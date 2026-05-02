"""
LAB 3 — A2A: Agent Card + Task Routing Between Two Agents
=========================================================
Goal:
  1. Serve an Agent Card at /.well-known/agent.json (FastAPI)
  2. Accept task requests at POST /tasks/send
  3. Build a client (client.py) that discovers and delegates to this agent

This file is the SERVER. Run the client in a separate terminal:
    Terminal 1:  uvicorn starter:app --reload --port 8001
    Terminal 2:  python client.py

Steps:
  1. Define the agent_card dict with name, description, url, skills
  2. Serve GET /.well-known/agent.json
  3. Define TaskRequest and TaskResponse Pydantic models
  4. Implement POST /tasks/send — calls an LLM and returns the result
  5. Add GET /tasks/{task_id} for status polling
  6. Test manually with curl, then run client.py

Time: ~15 minutes
"""

import os, uuid, asyncio
from typing import Optional
from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI
from pydantic import BaseModel

MODEL = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")

app = FastAPI(title="A2A Research Agent", version="1.0.0")

# In-memory task store (production would use a DB)
tasks: dict = {}


# ── TODO 1 ─────────────────────────────────────────────────────────────────────
# Define the Agent Card.
# This is a plain dict — it tells other agents what THIS agent can do.
#
# Required fields:
#   name:         str   — human-readable name
#   description:  str   — what the agent does
#   url:          str   — base URL where this agent is hosted
#   version:      str   — semver e.g. "1.0.0"
#   skills:       list  — list of skill objects, each with:
#                         id, name, description, inputModes, outputModes
#
# Example skill:
#   {
#     "id": "research",
#     "name": "Topic Research",
#     "description": "Researches a topic and returns a structured summary",
#     "inputModes": ["text"],
#     "outputModes": ["text"]
#   }

agent_card = {
    # TODO: fill in all fields
}


# ── TODO 2 ─────────────────────────────────────────────────────────────────────
# Serve the Agent Card at /.well-known/agent.json
# This is the A2A discovery endpoint — clients fetch it to learn your capabilities.
#
# @app.get("/.well-known/agent.json")
# async def get_agent_card():
#     return agent_card

# TODO: implement the discovery endpoint


# ── TODO 3 ─────────────────────────────────────────────────────────────────────
# Define Pydantic models for the task request and response.
#
# A2A Task Request:
#   id:      str                   — unique task ID (client provides)
#   message: dict                  — {"role": "user", "parts": [{"text": "..."}]}
#   skillId: Optional[str] = None  — which skill to invoke
#
# A2A Task Response:
#   id:      str   — same ID echoed back
#   status:  str   — "submitted" | "working" | "completed" | "failed"
#   result:  Optional[str] = None  — the agent's answer (when completed)
#   error:   Optional[str] = None  — error message (when failed)

class TaskRequest(BaseModel):
    pass  # TODO: add fields

class TaskResponse(BaseModel):
    pass  # TODO: add fields


# ── TODO 4 ─────────────────────────────────────────────────────────────────────
# Implement POST /tasks/send
#
# Flow:
#   a. Extract the user's text from request.message["parts"][0]["text"]
#   b. Store task as "working" in the tasks dict
#   c. Call the LLM with the user's text (import from openai or langchain_openai)
#   d. Update task status to "completed" with the LLM's response
#   e. Return a TaskResponse
#
# Error handling: catch all exceptions, set status="failed", set error=str(e)

# TODO: implement POST /tasks/send


# ── TODO 5 ─────────────────────────────────────────────────────────────────────
# Implement GET /tasks/{task_id}
# Returns the current state of a task (for polling).
# Return 404 if task_id not found.

# TODO: implement GET /tasks/{task_id}


# ── Health check (provided for you) ───────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "agent": agent_card.get("name", "unknown")}


# ── Run hint ──────────────────────────────────────────────────────────────────
# uvicorn starter:app --reload --port 8001

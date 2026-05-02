"""
LAB 1 — LangChain: Three Custom Tools + ReAct Agent
====================================================
Goal:
  Build 3 custom tools (currency converter, text stats, mock weather),
  wire them into a ReAct agent, and observe how the agent decides
  which tool to call for different queries.

Steps:
  1. Define @tool  currency_convert(amount, from_currency, to_currency)
  2. Define @tool  text_stats(text)
  3. Define StructuredTool  get_weather  with a Pydantic schema
  4. Create ReAct agent with all 3 tools
  5. Run with a multi-step query and observe tool selection
  6. Try additional queries that trigger different tools

Run:
    python starter.py

Time: ~15 minutes
Tip: verbose=True on AgentExecutor prints the full Thought/Action/Observation loop
"""

import os, json
from dotenv import load_dotenv
load_dotenv(override=True)

from langchain_groq import ChatGroq
from langchain_core.tools import tool, StructuredTool
from langchain import hub
from langchain_classic.agents import create_react_agent, AgentExecutor
from pydantic import BaseModel, Field

MODEL = os.getenv("OPENAI_MODEL_NAME", "llama-3.3-70b-versatile")
llm   = ChatGroq(model=MODEL, temperature=0)

# ── Exchange rates (hardcoded for the lab — no API key needed) ────────────────
RATES_TO_USD = {
    "USD": 1.0, "EUR": 1.08, "GBP": 1.27, "INR": 0.012,
    "JPY": 0.0067, "AUD": 0.65, "CAD": 0.73, "SGD": 0.74,
}

# ── TODO 1 ─────────────────────────────────────────────────────────────────────
# Create a @tool called 'currency_convert'.
#
# It should:
#   - Accept: amount (float), from_currency (str), to_currency (str)
#   - Convert via USD as a pivot: amount → USD → target
#   - Return a formatted string like: "100.0 USD = 92.59 EUR"
#   - Handle unknown currencies gracefully (return an error string)
#
# The docstring is what the LLM reads to decide when to call this tool —
# make it clear and specific.
#
# Hint:
#   @tool
#   def currency_convert(amount: float, from_currency: str, to_currency: str) -> str:
#       """Convert an amount from one currency to another. ..."""
#       ...

# TODO: implement currency_convert here


# ── TODO 2 ─────────────────────────────────────────────────────────────────────
# Create a @tool called 'text_stats'.
#
# It should:
#   - Accept: text (str)
#   - Return a JSON string with these keys:
#       word_count, char_count, sentence_count, avg_word_length, longest_word
#   - Use only the standard library (str.split, len, etc.)
#
# Hint: sentences end with '.', '!', or '?'

# TODO: implement text_stats here


# ── TODO 3 ─────────────────────────────────────────────────────────────────────
# Create a StructuredTool called 'get_weather' using a Pydantic input schema.
#
# Define a WeatherInput model with:
#   city: str           (required)
#   units: str = "celsius"   (optional, default celsius)
#
# The function returns a mock weather string like:
#   "Hyderabad: 34°C, partly cloudy, humidity 72%"
#
# Use a MOCK_WEATHER dict for a few cities; return a generic string for unknowns.
#
# Hint:
#   class WeatherInput(BaseModel):
#       city: str = Field(description="...")
#       units: str = Field(default="celsius", description="...")
#
#   def _get_weather_fn(city: str, units: str = "celsius") -> str: ...
#
#   get_weather = StructuredTool.from_function(
#       func=_get_weather_fn,
#       name="get_weather",
#       description="...",
#       args_schema=WeatherInput,
#   )

MOCK_WEATHER = {
    "hyderabad":  {"temp_c": 34, "condition": "partly cloudy",   "humidity": 72},
    "london":     {"temp_c": 14, "condition": "overcast",         "humidity": 85},
    "new york":   {"temp_c": 22, "condition": "sunny",            "humidity": 55},
    "tokyo":      {"temp_c": 26, "condition": "humid and hazy",   "humidity": 80},
    "sydney":     {"temp_c": 19, "condition": "clear skies",      "humidity": 60},
    "paris":      {"temp_c": 16, "condition": "light rain",       "humidity": 78},
    "frankfurt":  {"temp_c": 13, "condition": "cloudy",           "humidity": 70},
    "amsterdam":  {"temp_c": 12, "condition": "windy",            "humidity": 75},
    "singapore":  {"temp_c": 31, "condition": "thundery showers", "humidity": 88},
}

# TODO: implement WeatherInput and get_weather StructuredTool here


# ── TODO 4 ─────────────────────────────────────────────────────────────────────
# Build a ReAct agent using all 3 tools.
#
# Steps:
#   a. tools = [currency_convert, text_stats, get_weather]
#   b. Pull the standard ReAct prompt: hub.pull("hwchase17/react")
#   c. agent   = create_react_agent(llm, tools, prompt)
#   d. executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=6)
#
# Hint: the hub.pull call requires a HuggingFace/LangChain Hub account token
# if you hit a rate limit, use the FALLBACK_PROMPT below instead.

from langchain_core.prompts import PromptTemplate

FALLBACK_PROMPT = PromptTemplate.from_template("""Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}""")


def build_agent():
    # TODO: assemble tools list, agent, executor
    # Return the executor
    pass


# ── TODO 5 & 6 ────────────────────────────────────────────────────────────────
# Run the agent with these queries and observe the tool selection:
#
# Query A (multi-tool): "Convert 100 USD to EUR, then tell me the weather in the
#                        capital city of the country that uses EUR as its main currency."
#
# Query B (text tool):  "Analyse this text and give me statistics:
#                        The quick brown fox jumps over the lazy dog.
#                        Pack my box with five dozen liquor jugs."
#
# Query C (your choice): write your own query that uses 2+ tools

QUERIES = [
    "Convert 250 USD to INR and tell me the weather in New Delhi.",
    "What are the text statistics for: 'To be or not to be, that is the question. Whether tis nobler in the mind to suffer.'",
    "What is 500 EUR in GBP? Also, what is the weather in London in fahrenheit?",
]

def run():
    executor = build_agent()
    if executor is None:
        print("Complete TODO 4 (build_agent) first.")
        return

    for i, query in enumerate(QUERIES, 1):
        print(f"\n{'='*62}")
        print(f"Query {i}: {query}")
        print('='*62)
        result = executor.invoke({"input": query})
        print(f"\n✅ Final Answer: {result['output']}")


if __name__ == "__main__":
    print("Environment OK")
    run()

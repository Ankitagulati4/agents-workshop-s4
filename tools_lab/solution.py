"""
LAB 1 SOLUTION — LangChain: Three Custom Tools + ReAct Agent
=============================================================
Read only after attempting starter.py!
"""

import os, json
from dotenv import load_dotenv
load_dotenv(override=True)

from langchain_groq import ChatGroq
from langchain_core.tools import tool, StructuredTool
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

MODEL = os.getenv("OPENAI_MODEL_NAME", "llama-3.3-70b-versatile")
llm   = ChatGroq(model=MODEL, temperature=0)

# ── Exchange rates ────────────────────────────────────────────────────────────
RATES_TO_USD = {
    "USD": 1.0,  "EUR": 1.08, "GBP": 1.27, "INR": 0.012,
    "JPY": 0.0067, "AUD": 0.65, "CAD": 0.73, "SGD": 0.74,
    "CHF": 1.11,  "SEK": 0.095, "NZD": 0.61, "MXN": 0.058,
}

# ── Tool 1: Currency converter ────────────────────────────────────────────────
@tool
def currency_convert(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert a monetary amount from one currency to another.
    Supported currencies: USD, EUR, GBP, INR, JPY, AUD, CAD, SGD, CHF, SEK, NZD, MXN.
    Use this when the user asks to convert money or asks the value of an amount in another currency.
    """
    fc = from_currency.upper()
    tc = to_currency.upper()

    if fc not in RATES_TO_USD:
        return f"Unknown currency: {fc}. Supported: {', '.join(RATES_TO_USD)}"
    if tc not in RATES_TO_USD:
        return f"Unknown currency: {tc}. Supported: {', '.join(RATES_TO_USD)}"

    amount_in_usd    = amount / RATES_TO_USD[fc]   # to USD
    converted_amount = amount_in_usd * RATES_TO_USD[tc]  # to target

    return (
        f"{amount:,.2f} {fc} = {converted_amount:,.2f} {tc} "
        f"(rate: 1 {fc} = {RATES_TO_USD[tc]/RATES_TO_USD[fc]:.4f} {tc})"
    )


# ── Tool 2: Text statistics ────────────────────────────────────────────────────
@tool
def text_stats(text: str) -> str:
    """Analyse a piece of text and return statistics about it.
    Returns: word count, character count, sentence count, average word length,
    and the longest word. Use this when the user asks to analyse, count, or
    get statistics about a text passage.
    """
    import re
    words     = text.split()
    sentences = len(re.findall(r'[.!?]+', text)) or 1  # at least 1
    chars     = len(text)
    avg_len   = round(sum(len(w.strip(".,!?;:\"'")) for w in words) / max(len(words), 1), 2)
    longest   = max(words, key=lambda w: len(w.strip(".,!?;:\"'")), default="")

    stats = {
        "word_count":     len(words),
        "char_count":     chars,
        "sentence_count": sentences,
        "avg_word_length": avg_len,
        "longest_word":   longest.strip(".,!?;:\"'"),
    }
    return json.dumps(stats, indent=2)


# ── Tool 3: Weather (StructuredTool with Pydantic schema) ─────────────────────
MOCK_WEATHER = {
    "hyderabad":  {"temp_c": 34, "condition": "partly cloudy",   "humidity": 72},
    "london":     {"temp_c": 14, "condition": "overcast",         "humidity": 85},
    "new york":   {"temp_c": 22, "condition": "sunny",            "humidity": 55},
    "new delhi":  {"temp_c": 38, "condition": "very hot and hazy","humidity": 45},
    "tokyo":      {"temp_c": 26, "condition": "humid and hazy",   "humidity": 80},
    "sydney":     {"temp_c": 19, "condition": "clear skies",      "humidity": 60},
    "paris":      {"temp_c": 16, "condition": "light rain",       "humidity": 78},
    "frankfurt":  {"temp_c": 13, "condition": "cloudy",           "humidity": 70},
    "amsterdam":  {"temp_c": 12, "condition": "windy",            "humidity": 75},
    "singapore":  {"temp_c": 31, "condition": "thundery showers", "humidity": 88},
    "berlin":     {"temp_c": 15, "condition": "partly cloudy",    "humidity": 68},
    "mumbai":     {"temp_c": 32, "condition": "humid",            "humidity": 90},
}


class WeatherInput(BaseModel):
    city:  str = Field(description="The city name to get weather for, e.g. 'London'")
    units: str = Field(default="celsius", description="Temperature units: 'celsius' or 'fahrenheit'")


def _get_weather_fn(city: str, units: str = "celsius") -> str:
    key  = city.lower().strip()
    data = MOCK_WEATHER.get(key)

    if not data:
        # fuzzy match first word
        for k in MOCK_WEATHER:
            if key.split()[0] in k or k.split()[0] in key:
                data = MOCK_WEATHER[k]
                key  = k
                break

    if not data:
        return f"No weather data for '{city}'. Try: {', '.join(MOCK_WEATHER.keys())}"

    temp = data["temp_c"]
    if units.lower() == "fahrenheit":
        temp = round(temp * 9/5 + 32, 1)
        unit_sym = "°F"
    else:
        unit_sym = "°C"

    return (
        f"{city.title()}: {temp}{unit_sym}, {data['condition']}, "
        f"humidity {data['humidity']}%"
    )


get_weather = StructuredTool.from_function(
    func=_get_weather_fn,
    name="get_weather",
    description=(
        "Get the current weather for a city. Returns temperature, "
        "weather condition, and humidity. Use when the user asks about "
        "weather, temperature, or climate in a specific city."
    ),
    args_schema=WeatherInput,
)


# ── Tool-calling agent (uses Groq's native function-calling API) ──────────────
from langchain_core.prompts import ChatPromptTemplate

AGENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant with access to tools for currency conversion, "
               "text statistics, and weather. Use the tools when relevant. Answer concisely."),
    ("human",  "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])


def build_agent():
    tools     = [currency_convert, text_stats, get_weather]
    agent     = create_tool_calling_agent(llm, tools, AGENT_PROMPT)
    executor  = AgentExecutor(
        agent=agent, tools=tools,
        verbose=True, max_iterations=8,
        handle_parsing_errors=True,
    )
    return executor


# ── Test queries ──────────────────────────────────────────────────────────────
QUERIES = [
    # Multi-tool: currency + weather
    "Convert 250 USD to INR and tell me the weather in New Delhi.",
    # Single tool: text stats
    "What are the text statistics for: 'To be or not to be, that is the question. "
    "Whether tis nobler in the mind to suffer the slings and arrows of outrageous fortune.'",
    # Multi-tool: currency + weather + units
    "What is 500 EUR in GBP? Also, what is the weather in London in fahrenheit?",
    # Chained reasoning: convert, find city, get weather
    "Convert 100 USD to SGD. What's the weather like in Singapore?",
]


def run():
    executor = build_agent()

    print(f"\n{'='*62}")
    print("LangChain ReAct Agent — 3 Custom Tools")
    print(f"Model: {MODEL}")
    print('='*62)

    for i, query in enumerate(QUERIES, 1):
        print(f"\n{'─'*62}")
        print(f"Query {i}: {query}")
        print('─'*62)
        try:
            result = executor.invoke({"input": query})
            print(f"\n{'='*30}")
            print(f"✅ Final Answer: {result['output']}")
        except Exception as e:
            print(f"❌ Error: {e}")

    print(f"\n{'='*62}")
    print("💡 Observations to discuss:")
    print("  1. Did the agent always pick the right tool?")
    print("  2. How many Thought/Action cycles did it take?")
    print("  3. What happened with the multi-step currency → weather query?")
    print("  4. Try tweaking the tool docstrings — does tool selection change?")


if __name__ == "__main__":
    print("Environment OK")
    run()

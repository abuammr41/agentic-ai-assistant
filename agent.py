"""
agent.py
--------
A general-purpose AUTONOMOUS AI agent. Give it any goal in plain English —
it plans its own steps, decides which tools to use and in what order, and
keeps working until the goal is done, without asking for confirmation at
every step (unlike a simple chatbot that only answers one question at a
time).

Tools available to the agent:
  - web_search   : searches the web (DuckDuckGo, no API key required) and
                    returns the top results.
  - calculator    : evaluates a math expression safely.
  - read_file     : reads a local file.
  - write_file    : writes/creates a local file (e.g. to save a report).
  - list_dir      : lists files in a folder.

Supports TWO LLM providers — pick whichever API key you have:
  - Anthropic Claude  (set ANTHROPIC_API_KEY)
  - Google Gemini     (set GEMINI_API_KEY)
Set AGENT_PROVIDER=claude or AGENT_PROVIDER=gemini in .env to choose; if not
set, the agent auto-picks whichever key is present (Claude preferred).

Usage:
    pip install -r requirements.txt
    copy .env.example .env   (then fill in ONE api key)
    python agent.py "Research the top 3 AI agent frameworks and save a short comparison to report.md"

You can run everything EXCEPT the actual agent loop without any API key —
see test_tools.py, which tests each tool directly.
"""

import ast
import operator
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("AGENT_PROVIDER", "").lower()
if not PROVIDER:
    PROVIDER = "claude" if os.getenv("ANTHROPIC_API_KEY") else "gemini"

MAX_ITERATIONS = 20

SYSTEM_PROMPT = """You are a general-purpose autonomous AI agent. The user
gives you a goal — research a topic, calculate something, organize files,
write a report, or any combination of these.

Rules:
1. Break the goal into steps yourself; don't ask the user to clarify unless
   the goal is genuinely ambiguous.
2. Use the tools available to gather information and produce results. Decide
   yourself which tool to call, in what order, and how many times.
3. After each tool result, decide your next step yourself — keep going until
   the goal is fully done. Don't stop halfway to ask "should I continue?".
4. When finished, give one clear, concise final summary of what you did and
   the result (and where any file was saved, if applicable).

If a tool fails or returns an error, read the error and adjust your approach
(retry differently, or explain clearly why it can't be done)."""


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

TOOLS_SPEC = [
    {
        "name": "web_search",
        "description": "Searches the web and returns the top results (title + snippet + url) for a query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "calculator",
        "description": "Evaluates a math expression (e.g. '(120 * 3) / 7') and returns the numeric result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "A math expression."},
            },
            "required": ["expression"],
        },
    },
    {
        "name": "read_file",
        "description": "Reads the full text content of a local file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path."}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Writes (creates or overwrites) a local file with the given content. Creates folders as needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path."},
                "content": {"type": "string", "description": "Content to write."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_dir",
        "description": "Lists files and folders inside a given directory.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Folder path."}},
            "required": ["path"],
        },
    },
]

_SAFE_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg,
    ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Unsupported expression")


def calculator(expression: str) -> str:
    try:
        tree = ast.parse(expression, mode="eval")
        return str(_safe_eval(tree.body))
    except Exception as e:
        return f"Error: could not evaluate '{expression}' ({e})"


def web_search(query: str, max_results: int = 5) -> str:
    """Free web search via DuckDuckGo's HTML endpoint — no API key needed.

    Retries once after a short delay if the first attempt returns nothing,
    since DuckDuckGo occasionally rate-limits back-to-back requests.
    """
    import time

    from bs4 import BeautifulSoup

    last_error = None
    for attempt in range(2):
        try:
            resp = requests.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            resp.raise_for_status()
        except Exception as e:
            last_error = e
            time.sleep(2)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for result in soup.select(".result")[:max_results]:
            title_el = result.select_one(".result__a")
            snippet_el = result.select_one(".result__snippet")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            url = title_el.get("href", "")
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            results.append(f"- {title}\n  {url}\n  {snippet}")

        if results:
            return "\n".join(results)
        time.sleep(2)

    return f"No results found.{f' (last error: {last_error})' if last_error else ''}"


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()[:8000]


def write_file(path: str, content: str) -> str:
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Saved: {path}"


def list_dir(path: str) -> str:
    entries = os.listdir(path or ".")
    return "\n".join(entries) if entries else "(empty folder)"


def execute_tool(name: str, tool_input: dict) -> str:
    try:
        if name == "web_search":
            return web_search(tool_input["query"])
        if name == "calculator":
            return calculator(tool_input["expression"])
        if name == "read_file":
            return read_file(tool_input["path"])
        if name == "write_file":
            return write_file(tool_input["path"], tool_input["content"])
        if name == "list_dir":
            return list_dir(tool_input.get("path", "."))
        return f"Error: unknown tool '{name}'"
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Agent loop — Claude backend
# ---------------------------------------------------------------------------

def run_agent_claude(goal: str) -> str:
    import anthropic

    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": goal}]

    for step in range(MAX_ITERATIONS):
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS_SPEC,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return next((b.text for b in response.content if b.type == "text"), "")

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"  [step {step+1}] {block.name}({block.input})")
            result = execute_tool(block.name, block.input)
            print(f"           -> {result[:300]}")
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": result}
            )
        messages.append({"role": "user", "content": tool_results})

    return "Reached the safety step limit before finishing."


# ---------------------------------------------------------------------------
# Agent loop — Gemini backend
# ---------------------------------------------------------------------------

def _gemini_tool_declarations():
    import google.generativeai as genai

    return [
        genai.protos.FunctionDeclaration(
            name=t["name"],
            description=t["description"],
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    k: genai.protos.Schema(type=genai.protos.Type.STRING)
                    for k in t["input_schema"]["properties"]
                },
                required=t["input_schema"]["required"],
            ),
        )
        for t in TOOLS_SPEC
    ]


def run_agent_gemini(goal: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        system_instruction=SYSTEM_PROMPT,
        tools=_gemini_tool_declarations(),
    )
    chat = model.start_chat()
    response = chat.send_message(goal)

    for step in range(MAX_ITERATIONS):
        function_calls = [
            p.function_call for p in response.candidates[0].content.parts
            if p.function_call
        ]
        if not function_calls:
            return response.text

        parts = []
        for call in function_calls:
            tool_input = dict(call.args)
            print(f"  [step {step+1}] {call.name}({tool_input})")
            result = execute_tool(call.name, tool_input)
            print(f"           -> {result[:300]}")
            parts.append(
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=call.name, response={"result": result}
                    )
                )
            )
        response = chat.send_message(parts)

    return "Reached the safety step limit before finishing."


def run_agent(goal: str) -> str:
    if PROVIDER == "gemini":
        return run_agent_gemini(goal)
    return run_agent_claude(goal)


if __name__ == "__main__":
    goal_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Goal for the agent: ")
    print(f"\nGoal: {goal_text}\nProvider: {PROVIDER}\n")
    final_answer = run_agent(goal_text)
    print(f"\n=== Result ===\n{final_answer}")

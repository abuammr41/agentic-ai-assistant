# Agentic AI Assistant

A general-purpose **autonomous AI agent**: give it one goal in plain English,
and it plans its own steps, decides which tools to use and in what order, and
keeps working — calling tools, reading results, deciding the next step —
until the goal is fully done. Unlike a simple chatbot, you don't walk it
through each step; you give it the destination and it finds its own way
there.

## What it can do

The agent has 5 built-in tools and decides on its own which ones it needs:

| Tool | What it does |
|---|---|
| `web_search` | Searches the web (no API key needed) and returns top results |
| `calculator` | Evaluates math expressions |
| `read_file` | Reads a local file |
| `write_file` | Creates/overwrites a local file (e.g. to save a report) |
| `list_dir` | Lists files in a folder |

**Example goals it can handle end-to-end:**
- "Research the top 3 AI agent frameworks and save a short comparison to report.md"
- "Read data/notes.txt, summarize it, and save the summary to summary.txt"
- "Calculate compound interest on $5000 at 7% for 10 years and explain the result"

New tools (e.g. sending an email, calling a business API, scraping a specific
site) can be added the same way the 5 above were built — this is a starting
framework, not a fixed product.

## Supported AI providers

Works with **either** of these — use whichever API key you have:
- **Anthropic Claude** (`ANTHROPIC_API_KEY`)
- **Google Gemini** (`GEMINI_API_KEY`, has a free tier)

## Setup

```bash
pip install -r requirements.txt
copy .env.example .env      # then put your real API key inside .env
python agent.py "your goal here"
```

No API key yet? You can still verify the tools work on their own:

```bash
python test_tools.py
```

This tests `calculator`, `read_file`/`write_file`/`list_dir`, and
`web_search` directly, without needing any LLM API key — only the full
agent *reasoning* loop (deciding which tool to call and when) needs a key.

## How it works

1. You give the agent a goal.
2. The model (Claude or Gemini) reads the goal and the list of available
   tools, and decides whether it needs to call one.
3. If it calls a tool, the result is fed back to the model.
4. The model decides the next step itself — call another tool, or finish.
5. This repeats (capped at 20 steps as a safety limit) until the model
   produces a final answer instead of another tool call.

This "plan → act → observe → repeat" loop is what makes it *agentic* rather
than a single-turn Q&A bot.

## Project structure

```
agentic_ai_assistant/
  agent.py          # the agent loop + all 5 tools
  test_tools.py      # tests the tools without needing an API key
  requirements.txt
  .env.example
```

## Notes

- `web_search` uses DuckDuckGo's public HTML results page, so it needs no
  API key and no billing account.
- The agent is stateless between runs — each `python agent.py "..."` call
  starts a fresh goal. For a persistent/ongoing assistant, this loop can be
  wrapped in a long-running service.
- Custom tools for a specific business (e.g. your CRM, your inventory
  system, a specific website) can be added as a paid customization on top
  of this base.

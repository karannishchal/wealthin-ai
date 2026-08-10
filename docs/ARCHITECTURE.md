# Architecture

## Overview

WealthIn.AI is a tool-using agent. A request flows through the FastAPI backend into a
LangGraph state machine that alternates between an **agent node** (LLM decides what to do)
and a **tools node** (executes the chosen tools), looping until the model produces a final
answer or the step budget is reached.

```
                 ┌───────────────────────────────────────────────┐
   POST /chat    │                 LangGraph graph                │
  ────────────▶  │                                               │
                 │   START ─▶ [agent] ──route?── tools ─▶ [tools]│
   guardrails    │              ▲                         │      │
   (input)       │              └───────── loop ──────────┘      │
                 │              │                                 │
                 │              └─▶ END (final answer)            │
                 └───────────────────────────────────────────────┘
                          │
              guardrails (output) + disclaimer
                          │
                        answer + trace
```

## Components

### LLM layer (`app/llm.py`)
A single `chat(messages, tools)` function normalises four providers (Groq, Gemini,
Anthropic, OpenAI) to one `LLMResponse` shape. It runs a **fallback chain**: if the primary
provider errors or is rate-limited, the configured fallback is tried. This keeps a free
public demo resilient under bursty load. Tool schemas use the OpenAI function-calling format
and are converted per-provider.

### Agent (`app/agent.py`)
A LangGraph `StateGraph` with two nodes:
- **agent_node** — calls the LLM with the tool schemas; if the model requests tools, it
  appends an assistant tool-call message and routes to the tools node; otherwise it finalises.
- **tools_node** — executes each requested tool, appends tool-result messages, increments the
  step counter, and returns to the agent.

`_route` enforces the step budget (`MAX_AGENT_STEPS`) to prevent runaway loops and cost.
Every decision and tool call is recorded in a `trace` returned to the UI.

### Tools (`app/tools/`)
Each tool is a `Tool(name, description, parameters, func)` registered into a shared registry.
The registry produces the JSON schemas advertised to the LLM and executes calls by name. This
makes adding a tool a one-file change.

### Guardrails (`app/guardrails.py`)
- **Input:** rejects empty/oversized input, resists prompt-injection, flags personalised-advice.
- **Output:** softens advice-style answers and guarantees a *not-financial-advice* disclaimer.

### Observability (`app/observability.py`)
Structured JSON logging (structlog), an in-memory metrics registry (requests, errors, avg
latency, per-tool counts) exposed at `/metrics`, and a per-request step trace.

### Evaluation (`eval/`)
A golden set of queries with expected tool calls. `run_eval.py` scores tool-selection
accuracy and a groundedness proxy and exits non-zero below threshold, so it can gate CI.

## Request lifecycle

1. `POST /chat` → rate-limit check → input guardrail.
2. If no key configured → demo-mode canned response.
3. Otherwise → LangGraph agent runs (LLM ↔ tools loop).
4. Output guardrail applies disclaimer/softening.
5. Response returns `{answer, trace}`; metrics updated.

## Design decisions

- **LangGraph over a hand-rolled loop:** explicit, inspectable state machine; easy to add
  nodes (e.g. a verification step) and matches modern agentic-framework practice.
- **Provider fallback:** reliability and zero-cost operation for a public demo.
- **OpenAI-format messages internally:** one canonical message shape; adapters convert per provider.
- **Tools return plain dicts:** deterministic, unit-testable without the LLM.

## Extending

Add a tool: create `app/tools/<name>.py`, build a `Tool`, `register()` it, import it in
`app/tools/__init__.py`. It's immediately available to the agent and appears in `/metrics`.

"""Agentic orchestration built on LangGraph.

Canonical ReAct-style graph: an `agent` node calls the LLM (which may request
tools), a `tools` node executes them, and control loops back until the model
produces a final answer or the step budget is exhausted. State flows as
OpenAI-style message dicts so it works with the provider-agnostic LLM layer.
"""
from __future__ import annotations

import json
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.guardrails import apply_output_guardrails, check_input
from app.llm import ToolCall, chat
from app.observability import METRICS, get_logger
from app.tools import get as get_tool
from app.tools import schemas

log = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are WealthIn.AI, an investment-research assistant for a wealth-advisory "
    "context. Use the available tools to gather live market data, search documents "
    "and news, run calculations, and analyse portfolios before answering. "
    "Always ground claims in tool results and cite sources (tickers, filenames, "
    "news URLs) where possible. Be concise and objective. You must not give "
    "personalised buy/sell recommendations; provide balanced, factual research "
    "instead. If a tool returns an error, acknowledge it and continue."
)


class AgentState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    pending: list[ToolCall]
    steps: int
    trace: list[dict[str, Any]]
    answer: str


def _assistant_toolcall_msg(content: str, calls: list[ToolCall]) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": content or None,
        "tool_calls": [
            {
                "id": c.id,
                "type": "function",
                "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
            }
            for c in calls
        ],
    }


def agent_node(state: AgentState) -> AgentState:
    resp = chat(state["messages"], tools=schemas())
    trace = state.get("trace", [])
    if resp.wants_tools:
        msg = _assistant_toolcall_msg(resp.content, resp.tool_calls)
        trace = trace + [
            {"kind": "llm", "provider": resp.provider, "decided": "call_tools",
             "tools": [c.name for c in resp.tool_calls]}
        ]
        return {"messages": state["messages"] + [msg], "pending": resp.tool_calls, "trace": trace}
    trace = trace + [{"kind": "llm", "provider": resp.provider, "decided": "final_answer"}]
    return {
        "messages": state["messages"] + [{"role": "assistant", "content": resp.content}],
        "pending": [],
        "trace": trace,
        "answer": resp.content,
    }


def tools_node(state: AgentState) -> AgentState:
    messages = list(state["messages"])
    trace = list(state.get("trace", []))
    for call in state.get("pending", []):
        tool = get_tool(call.name)
        if tool is None:
            result: Any = {"error": f"Unknown tool '{call.name}'."}
        else:
            try:
                result = tool.run(call.arguments)
                METRICS.record_tool(call.name)
            except Exception as exc:  # noqa: BLE001 - surface tool errors to the model
                result = {"error": f"Tool '{call.name}' failed: {exc}"}
        trace.append({"kind": "tool", "name": call.name, "args": call.arguments})
        messages.append(
            {"role": "tool", "tool_call_id": call.id, "name": call.name, "content": json.dumps(result)}
        )
    return {"messages": messages, "pending": [], "steps": state.get("steps", 0) + 1, "trace": trace}


def _route(state: AgentState) -> str:
    if state.get("pending") and state.get("steps", 0) < settings.max_agent_steps:
        return "tools"
    return "end"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("agent", agent_node)
    g.add_node("tools", tools_node)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", _route, {"tools": "tools", "end": END})
    g.add_edge("tools", "agent")
    return g.compile()


_GRAPH = None


def _graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


def run_agent(user_message: str, history: list[dict] | None = None) -> dict[str, Any]:
    """Run one turn. Returns {answer, trace, provider-safe}."""
    guard = check_input(user_message)
    if not guard.allowed:
        return {"answer": guard.message, "trace": [{"kind": "guardrail", "action": "blocked"}]}

    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages += history
    messages.append({"role": "user", "content": user_message})

    state: AgentState = {"messages": messages, "pending": [], "steps": 0, "trace": []}
    result = _graph().invoke(state, config={"recursion_limit": settings.max_agent_steps * 2 + 4})

    answer = result.get("answer", "")
    if not answer:
        # Step budget hit while still calling tools — force a final, tool-free answer.
        final = chat(result["messages"] + [
            {"role": "user", "content": "Summarise your findings now in a final answer."}
        ])
        answer = final.content

    answer = apply_output_guardrails(answer, flagged_advice=guard.flagged_advice)
    return {"answer": answer, "trace": result.get("trace", [])}

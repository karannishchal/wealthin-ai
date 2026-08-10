"""Offline evaluation harness for the WealthIn.AI agent.

Runs each query in the golden set and scores two things:
  1. Tool-selection accuracy — did the agent call the expected tool?
  2. Groundedness proxy — did it return a non-empty, disclaimered answer?

Requires an LLM key (set GROQ_API_KEY). Run: `python -m eval.run_eval`.
Exits non-zero if accuracy falls below THRESHOLD, so it can gate CI.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

THRESHOLD = 0.7
GOLDEN = Path(__file__).parent / "golden_set.jsonl"


def load_cases() -> list[dict]:
    return [json.loads(line) for line in GOLDEN.read_text().splitlines() if line.strip()]


def tools_used(trace: list[dict]) -> set[str]:
    return {s.get("name") for s in trace if s.get("kind") == "tool"}


def main() -> int:
    from app.agent import run_agent

    cases = load_cases()
    tool_hits, grounded_hits = 0, 0
    print(f"Running {len(cases)} eval cases…\n")

    for case in cases:
        result = run_agent(case["query"])
        used = tools_used(result.get("trace", []))
        expected = set(case["expected_tools"])
        tool_ok = bool(expected & used)
        answer = result.get("answer", "")
        grounded = len(answer) > 40 and "not financial advice" in answer.lower()

        tool_hits += tool_ok
        grounded_hits += grounded
        print(f"[{'PASS' if tool_ok else 'MISS'}] {case['query'][:60]}")
        print(f"        expected={sorted(expected)} used={sorted(used)}")

    n = len(cases)
    tool_acc = tool_hits / n
    grounded_acc = grounded_hits / n
    print("\n--- Results ---")
    print(f"Tool-selection accuracy: {tool_acc:.0%}")
    print(f"Groundedness proxy:      {grounded_acc:.0%}")

    if tool_acc < THRESHOLD:
        print(f"\nFAIL: tool accuracy {tool_acc:.0%} < threshold {THRESHOLD:.0%}")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

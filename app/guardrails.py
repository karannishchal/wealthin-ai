"""Responsible-AI guardrails: input validation and output safety.

Kept deliberately simple and transparent — the goal is to demonstrate the
*practice* (scope control, injection resistance, mandatory disclaimer) that
the JPMorgan-style 'guardrail testing / Responsible AI' requirements call for.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

DISCLAIMER = (
    "\n\n---\n_WealthIn.AI provides educational research on public data only. "
    "This is not financial advice. Always do your own research or consult a "
    "qualified adviser before investing._"
)

MAX_INPUT_CHARS = 2000

# Rough prompt-injection / jailbreak signatures.
_INJECTION = re.compile(
    r"(ignore (all|previous|above) instructions|disregard .* (system|prompt)|"
    r"you are now|reveal your (system )?prompt|developer mode)",
    re.IGNORECASE,
)

# Signals the user is asking for a personalised recommendation we must soften.
_ADVICE = re.compile(r"\b(should i (buy|sell|invest)|what should i do with my money)\b", re.IGNORECASE)


@dataclass
class GuardResult:
    allowed: bool
    message: str = ""       # replacement/refusal text when not allowed
    flagged_advice: bool = False


def check_input(text: str) -> GuardResult:
    text = (text or "").strip()
    if not text:
        return GuardResult(False, "Please enter a question about a company, fund, or your portfolio.")
    if len(text) > MAX_INPUT_CHARS:
        return GuardResult(False, f"That message is too long (limit {MAX_INPUT_CHARS} characters).")
    if _INJECTION.search(text):
        return GuardResult(
            False,
            "I can only help with investment-research questions and can't change my "
            "instructions. Try asking about a company, fund, or portfolio.",
        )
    return GuardResult(True, flagged_advice=bool(_ADVICE.search(text)))


def apply_output_guardrails(answer: str, flagged_advice: bool = False) -> str:
    """Ensure a disclaimer is present and soften direct-advice phrasing."""
    answer = (answer or "").strip()
    if flagged_advice:
        answer = (
            "I can't give personalised buy/sell advice, but here's objective research "
            "to help you decide:\n\n" + answer
        )
    if "not financial advice" not in answer.lower():
        answer += DISCLAIMER
    return answer

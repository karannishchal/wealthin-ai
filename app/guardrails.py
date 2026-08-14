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


OFF_TOPIC_MESSAGE = (
    "I'm a focused **investment-research assistant**, so I stick to markets, companies, "
    "funds, economics, and personal-finance topics. Ask me things like *“What's a P/E "
    "ratio?”*, *“How did Nvidia perform this quarter?”*, or *“Analyse a 60/30/10 "
    "portfolio.”*"
)

_SCOPE_SYSTEM = (
    "You are a topic classifier for an investment-research assistant. Decide whether "
    "the user's message relates to investing, markets, stocks, companies, funds/ETFs, "
    "economics, personal finance, or any financial concept — including general or "
    "educational finance questions (e.g. 'what is a P/E ratio', 'how does inflation "
    "affect stocks'). Treat borderline or conceptual finance questions as RELEVANT. "
    "Only classify clearly-unrelated requests (coding help, recipes, general trivia, "
    "creative writing, personal chit-chat) as UNRELATED. "
    "Reply with exactly one word: RELEVANT or UNRELATED."
)


def is_in_scope(text: str) -> bool:
    """Lightweight model-judged scope check. Fails open (allows) on any error.

    Generous by design: only clearly off-topic requests are rejected, so
    conceptual finance questions are never wrongly blocked.
    """
    from app.llm import chat  # local import avoids a circular import at module load

    try:
        resp = chat(
            [
                {"role": "system", "content": _SCOPE_SYSTEM},
                {"role": "user", "content": (text or "")[:MAX_INPUT_CHARS]},
            ]
        )
        return "UNRELATED" not in resp.content.strip().upper()
    except Exception:  # noqa: BLE001 - never block on classifier failure
        return True


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

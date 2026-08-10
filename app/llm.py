"""Provider-agnostic LLM layer with an automatic fallback chain.

Exposes a single `chat()` call that takes OpenAI-style messages and tool
schemas and returns a normalised `LLMResponse`. If the primary provider
fails or is rate-limited, the configured fallback provider is tried next,
so the public demo stays up under load.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.observability import get_logger

log = get_logger(__name__)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    provider: str = ""

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


class LLMError(RuntimeError):
    """Raised when a provider call fails (so the fallback can take over)."""


# --------------------------------------------------------------------------- #
#  Individual provider adapters — all normalise to LLMResponse
# --------------------------------------------------------------------------- #
def _call_openai_compatible(
    provider: str, messages: list[dict], tools: list[dict] | None, model: str, api_key: str
) -> LLMResponse:
    """Groq and OpenAI share the OpenAI chat-completions/tool-calling schema."""
    if provider == "groq":
        from groq import Groq

        client = Groq(api_key=api_key)
    else:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

    kwargs: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.2}
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as exc:  # noqa: BLE001 - normalise all SDK errors
        raise LLMError(f"{provider} error: {exc}") from exc

    msg = resp.choices[0].message
    calls: list[ToolCall] = []
    for tc in msg.tool_calls or []:
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
    return LLMResponse(content=msg.content or "", tool_calls=calls, provider=provider)


# JSON-Schema keywords Gemini's function-declaration parser does not accept.
_GEMINI_UNSUPPORTED = {
    "default", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "minItems", "maxItems", "minLength", "maxLength", "additionalProperties",
}
_GEMINI_RESOLVED: str | None = None


def _gemini_clean(schema: Any) -> Any:
    """Recursively drop schema keywords Gemini rejects (e.g. 'default')."""
    if isinstance(schema, dict):
        return {k: _gemini_clean(v) for k, v in schema.items() if k not in _GEMINI_UNSUPPORTED}
    if isinstance(schema, list):
        return [_gemini_clean(x) for x in schema]
    return schema


def _pick_gemini_model(genai, preferred: str) -> str:
    """Resolve a model that this API key can actually call.

    Model names change/deprecate over time, so instead of hard-coding one we
    ask the API which models support `generateContent` and pick a Flash model
    (fast + free-tier friendly), falling back to the configured name.
    """
    global _GEMINI_RESOLVED
    if _GEMINI_RESOLVED:
        return _GEMINI_RESOLVED
    try:
        available = [
            m.name
            for m in genai.list_models()
            if "generateContent" in getattr(m, "supported_generation_methods", [])
        ]
    except Exception:  # noqa: BLE001 - if listing fails, just try the preferred name
        return preferred

    pref_full = preferred if preferred.startswith("models/") else f"models/{preferred}"
    if pref_full in available:
        _GEMINI_RESOLVED = preferred
        return preferred

    def _rank(name: str) -> tuple:
        # prefer flash, then newest-looking version number, avoid preview/vision
        flash = "flash" in name
        preview = "preview" in name or "exp" in name
        import re

        nums = re.findall(r"\d+\.?\d*", name)
        ver = float(nums[0]) if nums else 0.0
        return (flash, not preview, ver)

    candidates = [m for m in available if "vision" not in m and "embedding" not in m]
    chosen = max(candidates or available or [pref_full], key=_rank)
    _GEMINI_RESOLVED = chosen
    log.info("gemini_model_resolved", chosen=chosen)
    return chosen


def _gemini_history(messages: list[dict]) -> list[dict]:
    """Convert OpenAI-style messages to Gemini contents.

    Tool results and tool-call decisions are folded in as plain text so the
    model actually sees the tool outputs, and consecutive same-role turns are
    merged (Gemini requires alternating user/model roles).
    """
    turns: list[tuple[str, str]] = []
    for m in messages:
        role = m["role"]
        if role == "system":
            continue
        if role == "user":
            turns.append(("user", m.get("content", "")))
        elif role == "assistant":
            if m.get("content"):
                turns.append(("model", m["content"]))
            elif m.get("tool_calls"):
                names = ", ".join(tc["function"]["name"] for tc in m["tool_calls"])
                turns.append(("model", f"(calling tools: {names})"))
        elif role == "tool":
            turns.append(("user", f"Tool {m.get('name')} returned: {m.get('content', '')}"))

    merged: list[list] = []
    for r, text in turns:
        if merged and merged[-1][0] == r:
            merged[-1][1] += "\n" + text
        else:
            merged.append([r, text])
    return [{"role": r, "parts": [text]} for r, text in merged if text]


def _call_gemini(
    messages: list[dict], tools: list[dict] | None, model: str, api_key: str
) -> LLMResponse:
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    gem_tools = None
    if tools:
        gem_tools = [
            {
                "function_declarations": [
                    {
                        "name": t["function"]["name"],
                        "description": t["function"].get("description", ""),
                        "parameters": _gemini_clean(t["function"].get("parameters", {})),
                    }
                    for t in tools
                ]
            }
        ]
    system = "\n".join(m["content"] for m in messages if m["role"] == "system" and m.get("content"))
    history = _gemini_history(messages)

    def _run(mname: str):
        gmodel = genai.GenerativeModel(mname, system_instruction=system or None, tools=gem_tools)
        return gmodel.generate_content(history)

    model_name = _pick_gemini_model(genai, model)
    try:
        resp = _run(model_name)
    except Exception as exc:  # noqa: BLE001 - model may be dead; re-resolve once
        global _GEMINI_RESOLVED
        _GEMINI_RESOLVED = None
        alt = _pick_gemini_model(genai, "models/gemini-flash-latest")
        if alt and alt != model_name:
            try:
                resp = _run(alt)
            except Exception as exc2:  # noqa: BLE001
                raise LLMError(f"gemini error: {exc2}") from exc2
        else:
            raise LLMError(f"gemini error: {exc}") from exc

    calls: list[ToolCall] = []
    text = ""
    try:
        parts = resp.candidates[0].content.parts
    except (IndexError, AttributeError):
        parts = []
    for part in parts:
        fn = getattr(part, "function_call", None)
        if fn and getattr(fn, "name", ""):
            try:
                args = dict(fn.args) if fn.args else {}
            except Exception:  # noqa: BLE001
                args = {}
            calls.append(ToolCall(id=fn.name, name=fn.name, arguments=args))
        elif getattr(part, "text", None):
            text += part.text
    return LLMResponse(content=text, tool_calls=calls, provider="gemini")


def _call_anthropic(
    messages: list[dict], tools: list[dict] | None, model: str, api_key: str
) -> LLMResponse:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    convo = [m for m in messages if m["role"] in ("user", "assistant")]
    an_tools = None
    if tools:
        an_tools = [
            {
                "name": t["function"]["name"],
                "description": t["function"].get("description", ""),
                "input_schema": t["function"].get("parameters", {}),
            }
            for t in tools
        ]
    try:
        kwargs: dict[str, Any] = {"model": model, "max_tokens": 1024, "messages": convo}
        if system:
            kwargs["system"] = system
        if an_tools:
            kwargs["tools"] = an_tools
        resp = client.messages.create(**kwargs)
    except Exception as exc:  # noqa: BLE001
        raise LLMError(f"anthropic error: {exc}") from exc

    calls, text = [], ""
    for block in resp.content:
        if block.type == "text":
            text += block.text
        elif block.type == "tool_use":
            calls.append(ToolCall(id=block.id, name=block.name, arguments=dict(block.input)))
    return LLMResponse(content=text, tool_calls=calls, provider="anthropic")


def _dispatch(provider: str, messages: list[dict], tools: list[dict] | None) -> LLMResponse:
    api_key = settings.key_for(provider)
    model = settings.model_for(provider)
    if not api_key:
        raise LLMError(f"no API key configured for provider '{provider}'")
    if provider in ("groq", "openai"):
        return _call_openai_compatible(provider, messages, tools, model, api_key)
    if provider == "gemini":
        return _call_gemini(messages, tools, model, api_key)
    if provider == "anthropic":
        return _call_anthropic(messages, tools, model, api_key)
    raise LLMError(f"unknown provider '{provider}'")


# --------------------------------------------------------------------------- #
#  Public entry point with fallback chain
# --------------------------------------------------------------------------- #
def chat(messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
    """Call the primary provider; on failure, transparently try the fallback."""
    chain = [settings.llm_provider]
    if settings.llm_fallback and settings.llm_fallback != "none":
        chain.append(settings.llm_fallback)

    last_err: Exception | None = None
    for provider in chain:
        try:
            return _dispatch(provider, messages, tools)
        except LLMError as exc:
            last_err = exc
            log.warning("llm_provider_failed", provider=provider, error=str(exc))
            continue
    raise LLMError(f"all providers failed; last error: {last_err}")

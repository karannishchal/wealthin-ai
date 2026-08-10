"""Tests for the provider-agnostic LLM layer and its fallback chain."""
import app.llm as llm
from app.llm import LLMError, LLMResponse, chat


def test_fallback_used_when_primary_fails(monkeypatch):
    monkeypatch.setattr(llm.settings, "llm_provider", "groq")
    monkeypatch.setattr(llm.settings, "llm_fallback", "gemini")

    def fake_dispatch(provider, messages, tools):
        if provider == "groq":
            raise LLMError("rate limited")
        return LLMResponse(content="from fallback", provider=provider)

    monkeypatch.setattr(llm, "_dispatch", fake_dispatch)
    resp = chat([{"role": "user", "content": "hi"}])
    assert resp.content == "from fallback"
    assert resp.provider == "gemini"


def test_raises_when_all_fail(monkeypatch):
    monkeypatch.setattr(llm.settings, "llm_provider", "groq")
    monkeypatch.setattr(llm.settings, "llm_fallback", "gemini")

    def always_fail(provider, messages, tools):
        raise LLMError("down")

    monkeypatch.setattr(llm, "_dispatch", always_fail)
    try:
        chat([{"role": "user", "content": "hi"}])
        raise AssertionError("expected LLMError")
    except LLMError:
        pass

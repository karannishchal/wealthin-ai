"""Streamlit chat UI for WealthIn.AI.

Black / grey / orange theme. Runs in two modes:
  * API mode (default): talks to the FastAPI backend at API_URL.
  * In-process mode (INPROCESS=1): calls the agent directly, so the app can be
    hosted as a single container (e.g. Hugging Face Spaces) with no backend.
"""
from __future__ import annotations

import os
import sys

import requests
import streamlit as st

# Make the `app` package importable when run from a hosted Streamlit runtime
# (e.g. Streamlit Community Cloud) where the repo root isn't on sys.path by default.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# On Streamlit Community Cloud, config is provided via st.secrets. Mirror those
# values into the environment so pydantic Settings and the agent pick them up
# (e.g. GEMINI_API_KEY, INPROCESS). No-op locally when no secrets file exists.
try:
    for _k, _v in st.secrets.items():
        os.environ.setdefault(_k, str(_v))
except Exception:  # noqa: BLE001 - no secrets configured is fine
    pass

API_URL = os.environ.get("API_URL", "http://localhost:8000")
INPROCESS = os.environ.get("INPROCESS", "0") == "1"

st.set_page_config(page_title="WealthIn.AI", page_icon="📈", layout="centered")


def _safe_md(text: str) -> str:
    """Escape '$' so amounts like $10,000 don't render as LaTeX math."""
    return (text or "").replace("$", "\\$")


# --------------------------------------------------------------------------- #
#  Answer source: in-process agent or remote FastAPI backend
# --------------------------------------------------------------------------- #
PROVIDER_LABELS = {
    "groq": "Groq",
    "gemini": "Google Gemini",
    "anthropic": "Anthropic Claude",
    "openai": "OpenAI",
}


def provider_label(name: str) -> str:
    return PROVIDER_LABELS.get((name or "").lower(), (name or "AI").title())


def get_status() -> tuple[str, str]:
    """Return (badge_text, css_class). Shows the provider that last answered,
    falling back to the configured primary provider."""
    used = st.session_state.get("last_provider")
    if INPROCESS:
        from app.config import settings

        if settings.has_any_key():
            label = provider_label(used or settings.llm_provider)
            return f"🟢 Backend Online · Provider: {label}", "wi-badge"
        return "🟠 Demo mode · no LLM key set", "wi-badge wi-badge-off"
    try:
        h = requests.get(f"{API_URL}/health", timeout=5).json()
        if h.get("has_key"):
            label = provider_label(used or h.get("provider") or "gemini")
            return f"🟢 Backend Online · Provider: {label}", "wi-badge"
        return "🟠 Demo mode · no LLM key set", "wi-badge wi-badge-off"
    except Exception:  # noqa: BLE001
        return "🔴 Backend not reachable", "wi-badge wi-badge-off"


def get_answer(prompt: str, history: list[dict]) -> dict:
    if INPROCESS:
        from app.config import settings

        if not settings.has_any_key():
            from app.demo import demo_answer

            return demo_answer(prompt)
        from app.agent import run_agent

        try:
            result = run_agent(prompt, history=history)
            return {"answer": result.get("answer", ""), "trace": result.get("trace", [])}
        except Exception as exc:  # noqa: BLE001 - never crash the UI; surface the reason
            return {
                "answer": (
                    "⚠️ The AI provider couldn't be reached, so I can't answer live right now.\n\n"
                    f"**Reason:** `{exc}`\n\n"
                    "This is usually an API-key or quota issue on the host. "
                    "_(Educational demo — not financial advice.)_"
                ),
                "trace": [{"kind": "error", "detail": str(exc)}],
            }
    try:
        return requests.post(
            f"{API_URL}/chat",
            json={"message": prompt, "history": history},
            timeout=120,
        ).json()
    except Exception as exc:  # noqa: BLE001
        return {"answer": f"Request failed: {exc}", "trace": []}


st.markdown(
    """
    <style>
      #MainMenu, footer {visibility: hidden;}
      .stApp {background: #0F0F10;}
      .block-container {padding-top: 2.2rem; max-width: 820px;}
      .wi-head {display:flex; align-items:center; justify-content:center; gap:10px; margin-top:4px;}
      .wi-logo {width:30px; height:30px; border-radius:8px; background:#E8834A;
                display:inline-flex; align-items:center; justify-content:center;
                color:#151516; font-weight:700; font-size:16px;}
      .wi-name {font-size:1.9rem; font-weight:600; color:#F2F2F2; letter-spacing:-0.3px;}
      .wi-name span {color:#E8834A;}
      .wi-sub {text-align:center; color:#9B9B9F; font-family:ui-monospace,monospace;
               font-size:0.8rem; letter-spacing:0.4px; margin:6px 0 2px;}
      .wi-divider {height:1px; background:#242426; margin:14px 0 6px;}
      .wi-cap {text-align:center; color:#8A8A8E; font-size:0.85rem; margin-bottom:2px;}
      section[data-testid="stSidebar"] {background:#141415; border-right:1px solid #242426;}
      section[data-testid="stSidebar"] .stButton>button {
        width:100%; text-align:left; background:#1D1D1F; color:#D6D6D8;
        border:1px solid #2C2C2F; border-radius:9px; font-size:0.82rem; padding:8px 10px;}
      section[data-testid="stSidebar"] .stButton>button:hover {border-color:#E8834A; color:#F0A173;}
      .wi-badge {background:#17211A; border:1px solid #2C4A37; color:#7FC79B;
                 font-family:ui-monospace,monospace; font-size:0.72rem;
                 padding:8px 10px; border-radius:9px; margin-top:10px;}
      .wi-badge-off {background:#231A17; border-color:#4A342C; color:#E8A173;}
      [data-testid="stChatInput"] {background:#1A1A1C; border:1px solid #2C2C2F; border-radius:12px;}
      .wi-chip {display:inline-block; font-family:ui-monospace,monospace; font-size:0.72rem;
                color:#F0A173; background:rgba(232,131,74,0.14);
                border:1px solid rgba(232,131,74,0.30); border-radius:6px;
                padding:3px 8px; margin:2px 6px 2px 0;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="wi-head">
      <span class="wi-logo">W</span>
      <span class="wi-name">WealthIn<span>.AI</span></span>
    </div>
    <div class="wi-sub">Investment Research Assistant</div>
    <div class="wi-divider"></div>
    <div class="wi-cap">Ask about a stock or fund, compare companies, analyse a portfolio,
    or query your documents. Educational demo on public data — not financial advice.</div>
    """,
    unsafe_allow_html=True,
)

EXAMPLES = [
    "Compare Nvidia and AMD over the last 6 months and flag risks",
    "What's Apple's recent performance?",
    "Analyse a portfolio: 60% AAPL, 30% MSFT, 10% VOO",
    "Any recent news on the semiconductor sector?",
]

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending" not in st.session_state:
    st.session_state.pending = None

with st.sidebar:
    st.markdown("#### Try asking")
    for ex in EXAMPLES:
        if st.button(ex, key="ex_" + ex[:24]):
            st.session_state.pending = ex
    badge, cls = get_status()
    st.markdown(f'<div class="{cls}">{badge}</div>', unsafe_allow_html=True)

for m in st.session_state.messages:
    avatar = "🧑" if m["role"] == "user" else "📈"
    with st.chat_message(m["role"], avatar=avatar):
        st.markdown(_safe_md(m["content"]) if m["role"] == "assistant" else m["content"])

typed = st.chat_input("Ask an investment-research question…")
prompt = typed or st.session_state.pending
st.session_state.pending = None

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="📈"):
        with st.spinner("Researching…"):
            resp = get_answer(prompt, st.session_state.messages[:-1][-8:])

        st.markdown(_safe_md(resp.get("answer", "")))
        trace = resp.get("trace") or []
        provs = [s.get("provider") for s in trace if s.get("kind") == "llm" and s.get("provider")]
        if provs:
            st.session_state.last_provider = provs[-1]
        tools_used = [s.get("name") for s in trace if s.get("kind") == "tool"]
        if tools_used:
            chips = "".join(f'<span class="wi-chip">{t}</span>' for t in tools_used)
            with st.expander("🧠 How the agent answered (tool trace)"):
                st.markdown(chips, unsafe_allow_html=True)
                for step in trace:
                    if step.get("kind") == "llm":
                        st.caption(f"model · {step.get('provider')} → {step.get('decided')}")

    st.session_state.messages.append({"role": "assistant", "content": resp.get("answer", "")})

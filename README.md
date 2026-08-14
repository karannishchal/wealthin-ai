<div align="center">

# 📈 WealthIn.AI

**An agentic investment-research assistant.**
Ask it about a stock, compare companies, analyse a portfolio, or query your documents —
it *plans, calls tools, reasons, and answers with citations.*

`Python` · `LangGraph` · `FastAPI` · `RAG (FAISS)` · `Streamlit` · `Docker` · `GitHub Actions` · `Kubernetes`

### ▶ [Try the live demo → wealthin-ai.streamlit.app](https://wealthin-ai.streamlit.app/)

_Educational demo on public data — not financial advice._

</div>

---

## What it is

WealthIn.AI is an **AI assistant built on an agentic architecture**. Instead of a single
LLM call, a LangGraph agent decides *which tools to use, in what order,* and loops until it
can answer — grounding its response in live data and citing sources. It's built for a
wealth-advisory context (educational demo, public data, **not financial advice**).

It was built to demonstrate an end-to-end, production-minded GenAI system: agent
orchestration, retrieval, guardrails, evaluation, observability, containerisation, CI/CD
and Kubernetes.

## What it can do

The agent chooses from five tools:

| Tool | What it does |
|------|--------------|
| `get_market_data` | Live price performance & fundamentals (P/E, market cap, sector) via yfinance |
| `analyse_portfolio` | Position weights, sector allocation, concentration (HHI) risk |
| `search_documents` | RAG over your finance docs (FAISS + sentence-transformers) with source citations |
| `search_news` | Recent headlines/snippets via DuckDuckGo, with URLs |
| `calculate` | Precise arithmetic, so numbers are never hallucinated |

**Example:** *"Compare Nvidia and AMD over the last 6 months and flag risks for a cautious investor."*
→ the agent pulls market data for both, searches news, reasons over it, and returns a cited,
balanced answer with a disclaimer.

## Architecture

```
User ─▶ FastAPI ─▶ LangGraph agent ──▶ [ market_data | portfolio | documents(RAG) | news | calculator ]
                        │  ▲                         │
                        │  └──────── tool results ───┘
                        ▼
                guardrails + citations ─▶ answer
   (every step traced • metrics exposed • eval harness scores quality)
```

- **Provider-agnostic LLM layer** — **Gemini** by default, with an optional Groq fallback,
  so the free demo stays up under load. Anthropic/OpenAI available via `.env`.
- **Guardrails:** input validation, prompt-injection resistance, a mandatory
  *not-financial-advice* disclaimer, and softening of personalised-advice requests.
- **Observability:** structured JSON logs, a `/metrics` endpoint, and a per-request tool trace.
- **Evaluation:** an offline golden-set harness scoring tool-selection accuracy and
  groundedness — wired into CI.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for detail.

## Quickstart (local, free)

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure — you only need a free Gemini key
cp .env.example .env
#   then edit .env and set GEMINI_API_KEY=...   (get one free at https://aistudio.google.com/app/apikey)

# 3. Run the API and the UI (two terminals)
make run-api      # http://localhost:8000  (docs at /docs)
make run-ui       # http://localhost:8501

# Or run both in containers:
docker compose up --build
```

No key yet? The app runs in **demo mode** and returns a canned example, so it never breaks.

## Test, lint, evaluate

```bash
make test     # pytest (unit tests, mocked LLM — no key needed)
make lint     # ruff
make eval     # offline agent evaluation (needs a key)
```

## Deploy

- **Container host (simplest):** any platform that runs a Docker image (Render, Railway, Fly.io).
  Point it at the `Dockerfile`, set `GEMINI_API_KEY`, expose port 8000.
- **Kubernetes:** manifests in [`k8s/`](k8s/). Create the secret, then `kubectl apply -f k8s/`.
  A local cluster (`kind`/`minikube`) is enough to demonstrate orchestration.

```bash
kubectl create namespace wealthin
kubectl -n wealthin create secret generic wealthin-secrets --from-literal=GEMINI_API_KEY=your_key
kubectl apply -f k8s/
```

## Tech stack

Python 3.11 · LangGraph · Groq/Gemini/Anthropic/OpenAI · FastAPI · Pydantic · FAISS +
sentence-transformers · yfinance · DuckDuckGo · Streamlit · structlog · pytest · ruff ·
Docker · GitHub Actions · Kubernetes.

## Responsible AI

Educational demo on public data. It refuses to give personalised buy/sell advice, always
appends a disclaimer, resists prompt-injection, and rate-limits requests. Not affiliated
with any financial institution.

---

<div align="center">
Built by <a href="https://karannishchal.netlify.app">Karan Nishchal</a> ·
<a href="https://github.com/karannishchal">GitHub</a> ·
<a href="https://www.linkedin.com/in/karannishchal/">LinkedIn</a>
</div>

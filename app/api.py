"""FastAPI backend for WealthIn.AI."""

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app import __version__
from app.config import settings
from app.demo import demo_answer
from app.observability import METRICS, get_logger
from app.schemas import ChatRequest, ChatResponse

log = get_logger("api")
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="WealthIn.AI", version=__version__)
app.state.limiter = limiter
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

_RATE = f"{settings.rate_limit_per_minute}/minute"


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "answer": "You're sending requests a little fast — please wait a moment and retry.",
            "trace": [],
            "demo_mode": False,
        },
    )


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "provider": settings.llm_provider,
        "has_key": settings.has_any_key(),
    }


@app.get("/metrics")
def metrics() -> dict:
    return METRICS.snapshot()


@app.post("/chat", response_model=ChatResponse)
@limiter.limit(_RATE)
def chat_endpoint(request: Request, body: ChatRequest) -> ChatResponse:
    start = time.perf_counter()

    # No key configured -> serve the canned demo so the page still works.
    if not settings.has_any_key():
        METRICS.record_request((time.perf_counter() - start) * 1000, error=not settings.demo_mode)
        if settings.demo_mode:
            return ChatResponse(**demo_answer(body.message))
        return ChatResponse(
            answer="No LLM provider is configured. Set GROQ_API_KEY in .env.",
            trace=[],
            demo_mode=False,
        )

    from app.agent import run_agent

    try:
        history = [{"role": m.role, "content": m.content} for m in body.history][-8:]
        result = run_agent(body.message, history=history)
        METRICS.record_request((time.perf_counter() - start) * 1000)
        return ChatResponse(answer=result["answer"], trace=result.get("trace", []), demo_mode=False)
    except Exception as exc:  # noqa: BLE001 - never crash the endpoint for the user
        log.error("chat_failed", error=str(exc))
        METRICS.record_request((time.perf_counter() - start) * 1000, error=True)
        return ChatResponse(
            answer="Something went wrong handling that request. Please try again.",
            trace=[],
            demo_mode=False,
        )

"""Structured logging, lightweight metrics, and per-request step tracing."""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

import structlog

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )
    _configured = True


def get_logger(name: str = "wealthin"):
    _configure()
    return structlog.get_logger(name)


# --------------------------------------------------------------------------- #
#  In-memory metrics (exposed via /metrics) — good enough for a demo
# --------------------------------------------------------------------------- #
@dataclass
class Metrics:
    requests: int = 0
    errors: int = 0
    tool_calls: dict[str, int] = field(default_factory=dict)
    total_latency_ms: float = 0.0
    _lock: Lock = field(default_factory=Lock)

    def record_request(self, latency_ms: float, error: bool = False) -> None:
        with self._lock:
            self.requests += 1
            self.total_latency_ms += latency_ms
            if error:
                self.errors += 1

    def record_tool(self, name: str) -> None:
        with self._lock:
            self.tool_calls[name] = self.tool_calls.get(name, 0) + 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            avg = self.total_latency_ms / self.requests if self.requests else 0.0
            return {
                "requests": self.requests,
                "errors": self.errors,
                "avg_latency_ms": round(avg, 1),
                "tool_calls": dict(self.tool_calls),
            }


METRICS = Metrics()


@dataclass
class Trace:
    """Ordered record of each step the agent took (for observability/UI)."""

    steps: list[dict[str, Any]] = field(default_factory=list)

    def add(self, kind: str, **data: Any) -> None:
        self.steps.append({"kind": kind, **data})


@contextmanager
def timed(logger, event: str, **ctx: Any):
    start = time.perf_counter()
    try:
        yield
    finally:
        logger.info(event, elapsed_ms=round((time.perf_counter() - start) * 1000, 1), **ctx)

"""Tool abstraction + registry shared by every tool."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

_REGISTRY: dict[str, Tool] = {}


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema (OpenAI function-calling format)
    func: Callable[..., Any]

    def to_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def run(self, args: dict[str, Any]) -> Any:
        return self.func(**args)


def register(tool: Tool) -> Tool:
    _REGISTRY[tool.name] = tool
    return tool


def get(name: str) -> Tool | None:
    return _REGISTRY.get(name)


def all_tools() -> list[Tool]:
    return list(_REGISTRY.values())


def schemas() -> list[dict[str, Any]]:
    return [t.to_schema() for t in _REGISTRY.values()]

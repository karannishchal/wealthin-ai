"""Calculator tool — safe arithmetic so the agent never hallucinates maths."""
from __future__ import annotations

import ast
import operator as op

from app.tools.base import Tool, register

_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int | float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Unsupported expression")


def _calculate(expression: str) -> dict:
    """Safely evaluate an arithmetic expression (no names/calls allowed)."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval(tree.body)
        return {"expression": expression, "result": round(result, 6)}
    except Exception:  # noqa: BLE001
        return {"expression": expression, "error": "Invalid or unsupported expression."}


register(
    Tool(
        name="calculate",
        description=(
            "Evaluate a numeric arithmetic expression precisely (e.g. compound "
            "growth, weighted averages, percentage changes). Use for any maths."
        ),
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression, e.g. '(1450-1200)/1200*100'.",
                }
            },
            "required": ["expression"],
        },
        func=_calculate,
    )
)

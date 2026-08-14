"""Importing this package registers every tool into the shared registry.

The document-RAG tool pulls in heavy deps (sentence-transformers / torch). On
memory-constrained hosts set DISABLE_DOC_TOOL=1 to skip it; the other tools and
the full agent still work.
"""
import os

from app.tools import calculator, market_data, news, portfolio  # noqa: F401
from app.tools.base import all_tools, get, schemas

if os.environ.get("DISABLE_DOC_TOOL", "0") != "1":
    from app.tools import documents  # noqa: F401

__all__ = ["all_tools", "get", "schemas"]

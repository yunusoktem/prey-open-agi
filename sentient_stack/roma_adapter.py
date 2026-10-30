"""Opt-in adapter for Sentient's official ROMA-DSPy solver.

This module is intentionally isolated from the Flask request path. It requires
an explicitly provisioned ROMA environment and an OpenAI API key matching the
official package's default gpt-4o-mini model configuration. It never silently
falls back to Fortytwo or changes the existing workspace.
"""
from __future__ import annotations

import importlib.util
import os
from typing import Any


class ROMAUnavailable(RuntimeError):
    """ROMA was requested but its runtime or provider is unavailable."""


def is_roma_available() -> bool:
    if os.getenv("PREY_ROMA_ENABLED", "").strip().lower() not in {"1", "true", "yes"}:
        return False
    try:
        if importlib.util.find_spec("roma_dspy") is None:
            return False
    except (ImportError, ModuleNotFoundError, ValueError):
        return False

    # The upstream ROMAConfig defaults to model="gpt-4o-mini". An OpenRouter
    # or Anthropic key alone does not authenticate that model. Require the
    # matching OpenAI credential rather than claiming unsupported compatibility.
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def run_roma(task: str, *, max_depth: int = 1) -> str:
    """Run official ROMA with a shallow, bounded recursion depth.

    ROMA uses its default gpt-4o-mini model through OpenAI. This function is
    never called unless the operator enables it and supplies that provider key.
    """
    task = (task or "").strip()
    if not task:
        raise ValueError("ROMA task cannot be empty.")
    if len(task) > 12000:
        raise ValueError("ROMA task exceeds the 12,000-character limit.")
    if not is_roma_available():
        raise ROMAUnavailable(
            "ROMA is disabled or its optional package/OpenAI credentials are missing."
        )
    try:
        from roma_dspy.core.engine.solve import solve
        result: Any = solve(task, max_depth=max(1, min(int(max_depth), 2)))
    except Exception as exc:
        raise ROMAUnavailable("ROMA execution failed; inspect server logs.") from exc

    if hasattr(result, "model_dump"):
        result = result.model_dump()
    elif hasattr(result, "dict"):
        result = result.dict()
    if isinstance(result, dict):
        text = (
            result.get("result")
            or result.get("output")
            or result.get("goal")
            or str(result)
        )
    else:
        text = (
            getattr(result, "result", None)
            or getattr(result, "output", None)
            or str(result)
        )
    return str(text).strip()

"""Optional OpenDeepSearch adapter for Prey Open AGI.

ODS is deliberately optional: the default application does not import its heavy
ML/browser dependency tree or incur extra model/search charges. Enable it only
after configuring the provider, reranker and model credentials documented by ODS.
"""
from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)


class ODSError(RuntimeError):
    """Raised when ODS was requested but is unavailable or misconfigured."""


def is_ods_configured() -> bool:
    provider = os.getenv("ODS_SEARCH_PROVIDER", "serper").strip().lower()
    has_search = (
        bool(os.getenv("SERPER_API_KEY"))
        if provider == "serper"
        else bool(os.getenv("SEARXNG_INSTANCE_URL"))
        if provider == "searxng"
        else False
    )
    reranker = os.getenv("ODS_RERANKER", "jina").strip().lower()
    has_reranker = reranker == "none" or (
        bool(os.getenv("JINA_API_KEY")) if reranker == "jina" else False
    )
    return has_search and has_reranker and bool(os.getenv("ODS_MODEL_NAME"))


def search_with_ods(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Run ODS only when explicitly enabled and fully configured."""
    if os.getenv("ODS_ENABLED", "false").strip().lower() not in {"1", "true", "yes"}:
        raise ODSError("ODS is disabled. Set ODS_ENABLED=true to enable it.")
    if not is_ods_configured():
        raise ODSError(
            "ODS configuration is incomplete. Check ODS_SEARCH_PROVIDER, "
            "ODS_MODEL_NAME, search-provider credentials and reranker settings."
        )
    query = (query or "").strip()
    if not query:
        raise ValueError("ODS query cannot be empty.")

    try:
        from opendeepsearch import OpenDeepSearchTool
    except ImportError as exc:
        raise ODSError(
            "OpenDeepSearch is not installed in this environment. "
            "Install and validate it in a separate deployment image first."
        ) from exc

    provider = os.getenv("ODS_SEARCH_PROVIDER", "serper").strip().lower()
    reranker = os.getenv("ODS_RERANKER", "jina").strip().lower()
    kwargs: dict[str, Any] = {
        "model_name": os.environ["ODS_MODEL_NAME"],
        "reranker": None if reranker == "none" else reranker,
    }
    if provider == "searxng":
        kwargs.update({
            "search_provider": "searxng",
            "searxng_instance_url": os.environ["SEARXNG_INSTANCE_URL"],
            "searxng_api_key": os.getenv("SEARXNG_API_KEY"),
        })
    try:
        tool = OpenDeepSearchTool(**kwargs)
        if not getattr(tool, "is_initialized", False):
            tool.setup()
        raw = tool.forward(query)
    except Exception as exc:
        log.exception("OpenDeepSearch request failed")
        raise ODSError("OpenDeepSearch request failed; see server logs.") from exc

    # ODS versions may return either text or a structured object. Preserve the
    # original output as source material; do not fabricate individual citations.
    if isinstance(raw, str):
        content = raw.strip()
    elif isinstance(raw, dict):
        content = str(raw.get("content") or raw.get("result") or raw).strip()
    else:
        content = str(raw).strip()
    if not content:
        return []
    return [{
        "baslik": "OpenDeepSearch research result",
        "url": "",
        "aciklama": content[:12000],
        "icerik": content[:12000],
        "source_engine": "ods",
    }][:max(1, min(int(max_results), 10))]

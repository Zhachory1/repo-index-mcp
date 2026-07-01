from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from repo_index_mcp.engine import DEFAULT_DB_PATH, RepoIndex
from repo_index_mcp.usage import log_search_event


def run_server(*, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install codescry with the mcp dependency to run serve") from exc

    engine = RepoIndex(db_path=db_path)
    mcp = FastMCP("codescry")

    @mcp.tool()
    def search_code(
        query: str,
        repo: str | None = None,
        path_prefix: str | None = None,
        language: str | None = None,
        k: int = 10,
    ) -> list[dict[str, Any]]:
        """Search indexed code and return ranked snippets with file locations."""
        start = time.monotonic()
        results = engine.query(
            query,
            repo=repo,
            path_prefix=path_prefix,
            language=language,
            k=k,
        )
        log_search_event(
            tool="search_code",
            query=query,
            source="mcp",
            latency_ms=int((time.monotonic() - start) * 1000),
            results=results,
            repo=repo,
            path_prefix=path_prefix,
            language=language,
            k=k,
        )
        return [asdict(result) for result in results]

    @mcp.tool()
    def get_symbol(name: str, repo: str | None = None) -> dict[str, Any] | None:
        """Look up a symbol from indexed metadata, falling back to search."""
        start = time.monotonic()
        result = engine.get_symbol(name, repo=repo)
        if result is None:
            log_search_event(
                tool="get_symbol",
                query=name,
                source="mcp",
                latency_ms=int((time.monotonic() - start) * 1000),
                results=[],
                repo=repo,
                k=1,
            )
            return None
        log_search_event(
            tool="get_symbol",
            query=name,
            source="mcp",
            latency_ms=int((time.monotonic() - start) * 1000),
            results=[result],
            repo=repo,
            k=1,
        )
        return {
            "repo": result.repo,
            "path": result.path,
            "start_line": result.start_line,
            "end_line": result.end_line,
            "definition": result.snippet,
            "score": result.score,
            "symbol_name": result.symbol_name,
            "symbol_kind": result.symbol_kind,
            "symbol_confidence": result.symbol_confidence,
            "is_stale": result.is_stale,
            "has_dirty_tracked_files": result.has_dirty_tracked_files,
        }

    @mcp.tool()
    def list_repos() -> list[dict[str, Any]]:
        """List indexed repos and freshness state."""
        return engine.list_repos()

    @mcp.tool()
    def reindex(repo_path: str | None = None) -> dict[str, Any]:
        """Reindex a repo. Path optional only when exactly one repo is indexed."""
        return asdict(engine.reindex(repo_path))

    mcp.run()

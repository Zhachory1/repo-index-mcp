from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import statistics
import time
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from repo_index_mcp.models import SearchResult

USAGE_DIR = Path.home() / ".codescry"
DEFAULT_USAGE_LOG = USAGE_DIR / "usage.jsonl"
TEXT_ID_SALT = USAGE_DIR / "usage_salt"


def usage_log_path(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path).expanduser()
    configured = os.environ.get("CODESCRY_USAGE_LOG")
    return Path(configured).expanduser() if configured else DEFAULT_USAGE_LOG


def write_event(
    event: dict[str, Any],
    *,
    path: str | Path | None = None,
    strict: bool = False,
) -> bool:
    if os.environ.get("CODESCRY_DISABLE_USAGE_LOG") == "1":
        return True
    target = usage_log_path(path)
    payload = {"ts": time.time(), **event}
    try:
        ensure_log_parent(target)
        if target.exists():
            target.chmod(0o600)
        fd = os.open(target, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as file:
            file.write(json.dumps(payload, sort_keys=True) + "\n")
        target.chmod(0o600)
        return True
    except OSError:
        if strict:
            raise
        return False


def read_events(path: str | Path | Sequence[str | Path] | None = None) -> list[dict[str, Any]]:
    events, _bad_line_count = read_events_with_bad_count(path)
    return events


def read_events_with_bad_count(
    path: str | Path | Sequence[str | Path] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    paths = [usage_log_path()] if path is None else normalize_paths(path)
    events: list[dict[str, Any]] = []
    bad_line_count = 0
    for target in paths:
        if not target.exists():
            continue
        with target.open(encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    event = json.loads(stripped)
                except json.JSONDecodeError:
                    bad_line_count += 1
                    continue
                if isinstance(event, dict):
                    events.append(event)
                else:
                    bad_line_count += 1
    return events, bad_line_count


def normalize_paths(path: str | Path | Sequence[str | Path]) -> list[Path]:
    if isinstance(path, str | Path):
        return [Path(path).expanduser()]
    return [Path(item).expanduser() for item in path]


def ensure_log_parent(target: Path) -> None:
    if target.parent == USAGE_DIR:
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.parent.chmod(0o700)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)


def log_search_event(
    *,
    tool: str,
    query: str,
    source: str,
    latency_ms: int,
    results: list[SearchResult],
    repo: str | None = None,
    path_prefix: str | None = None,
    language: str | None = None,
    k: int | None = None,
) -> None:
    if os.environ.get("CODESCRY_ENABLE_USAGE_LOG") != "1":
        return
    try:
        event = {
            "event": "search",
            "tool": tool,
            "source": source,
            **text_payload("query", query),
            "repo": repo,
            "path_prefix": path_prefix,
            "language": language,
            "k": k,
            "latency_ms": latency_ms,
            "result_count": len(results),
            "top_paths": [result.path for result in results[:5]],
            "top_repos": [result.repo for result in results[:5]],
            "stale_count": sum(1 for result in results if result.is_stale),
            "dirty_count": sum(1 for result in results if result.has_dirty_tracked_files),
        }
    except OSError:
        return
    write_event(event)


def start_task(
    *,
    engineer: str,
    task: str,
    task_class: str | None,
    repos: list[str],
) -> dict[str, Any]:
    task_id = f"pilot-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    event = {
        "event": "task_start",
        "task_id": task_id,
        "engineer": engineer,
        **text_payload("task", task),
        "task_class": task_class,
        "repos": repos,
    }
    write_event(event, strict=True)
    return event


def end_task(
    *,
    task_id: str,
    engineer: str,
    baseline_source: str,
    baseline_minutes: float | None,
    tool_minutes: float | None,
    baseline_files_pasted: int | None,
    tool_files_pasted: int | None,
    mcp_queries: int | None,
    useful: bool | None,
    decision_grade: bool,
    notes: str | None,
) -> dict[str, Any]:
    if tool_minutes is None:
        start = next(
            (event for event in reversed(read_events()) if event.get("task_id") == task_id),
            None,
        )
        if start and start.get("event") == "task_start":
            tool_minutes = round((time.time() - float(start["ts"])) / 60.0, 3)
    event = {
        "event": "task_end",
        "task_id": task_id,
        "engineer": engineer,
        "baseline_source": baseline_source,
        "baseline_minutes": baseline_minutes,
        "tool_minutes": tool_minutes,
        "baseline_files_pasted": baseline_files_pasted,
        "tool_files_pasted": tool_files_pasted,
        "mcp_queries": mcp_queries,
        "useful": useful,
        "decision_grade": decision_grade,
        **text_payload("notes", notes),
    }
    write_event(event, strict=True)
    return event


def record_activation(
    *,
    engineer: str,
    client: str,
    repo: str | None,
    doctor_ok: bool,
    repo_indexed: bool,
    tools_visible: bool,
    list_repos_ok: bool,
    search_code_ok: bool,
    relevant_result: bool,
    notes: str | None,
) -> dict[str, Any]:
    event = {
        "event": "activation",
        "engineer": engineer,
        "client": client,
        "repo": repo,
        "doctor_ok": doctor_ok,
        "repo_indexed": repo_indexed,
        "tools_visible": tools_visible,
        "list_repos_ok": list_repos_ok,
        "search_code_ok": search_code_ok,
        "relevant_result": relevant_result,
        **text_payload("notes", notes),
    }
    write_event(event, strict=True)
    return event


def record_retention(
    *,
    engineer: str,
    enabled: bool,
    week2: bool,
    notes: str | None,
) -> dict[str, Any]:
    event = {
        "event": "retention",
        "engineer": engineer,
        "enabled": enabled,
        "week2": week2,
        **text_payload("notes", notes),
    }
    write_event(event, strict=True)
    return event


def record_miss(
    *,
    raw_query: str | None,
    expected_path: str | None,
    expected_text: str | None,
    scrubbed_query: str,
    scrubbed_expected_text: str | None,
    notes: str | None,
) -> dict[str, Any]:
    event = {
        "event": "miss",
        **text_payload("raw_query", raw_query),
        "scrubbed_query": scrubbed_query,
        "expected_path": expected_path,
        **text_payload("expected_text", expected_text),
        "scrubbed_expected_text": scrubbed_expected_text,
        **text_payload("notes", notes),
    }
    write_event(event, strict=True)
    return event


def build_report(path: str | Path | Sequence[str | Path] | None = None) -> dict[str, Any]:
    events, bad_line_count = read_events_with_bad_count(path)
    activations = [event for event in events if event.get("event") == "activation"]
    searches = [event for event in events if event.get("event") == "search"]
    task_starts = [event for event in events if event.get("event") == "task_start"]
    task_ends = [event for event in events if event.get("event") == "task_end"]
    retentions = [event for event in events if event.get("event") == "retention"]
    decision_grade = [event for event in task_ends if event.get("decision_grade")]
    misses = [event for event in events if event.get("event") == "miss"]

    valid_activation_events = [event for event in activations if is_valid_activation(event)]
    activated_engineers = {
        event.get("engineer") for event in valid_activation_events if event.get("engineer")
    }
    valid_decision_grade, duplicate_task_end_count = valid_decision_grade_events(
        decision_grade,
        task_starts,
    )
    baseline_minutes = numeric_values(valid_decision_grade, "baseline_minutes")
    tool_minutes = numeric_values(valid_decision_grade, "tool_minutes")
    baseline_pastes = numeric_values(valid_decision_grade, "baseline_files_pasted")
    tool_pastes = numeric_values(valid_decision_grade, "tool_files_pasted")
    context_reductions = row_reductions(valid_decision_grade, "baseline_minutes", "tool_minutes")
    paste_reductions = row_reductions(
        valid_decision_grade,
        "baseline_files_pasted",
        "tool_files_pasted",
    )
    query_latencies = numeric_values(searches, "latency_ms")
    context_reduction = median(context_reductions)
    paste_reduction = median(paste_reductions)
    latest_retention = latest_week2_retention_by_engineer(retentions)
    retained_engineers = {
        engineer
        for engineer, enabled in latest_retention.items()
        if engineer in activated_engineers and enabled is True
    }
    retention_rate = ratio(len(retained_engineers), len(activated_engineers))
    tasks_by_engineer = valid_tasks_by_engineer(valid_decision_grade, activated_engineers)

    return {
        "events": len(events),
        "bad_line_count": bad_line_count,
        "duplicate_task_end_count": duplicate_task_end_count,
        "activated_engineer_ids": sorted(
            stable_text_id(str(engineer)) for engineer in activated_engineers
        ),
        "activation_count": len(activated_engineers),
        "search_count": len(searches),
        "zero_result_rate": ratio(
            sum(1 for event in searches if event.get("result_count") == 0),
            len(searches),
        ),
        "median_query_latency_ms": median(query_latencies),
        "completed_tasks": len(task_ends),
        "decision_grade_tasks": len(decision_grade),
        "valid_decision_grade_tasks": len(valid_decision_grade),
        "median_baseline_minutes": median(baseline_minutes),
        "median_tool_minutes": median(tool_minutes),
        "context_minutes_reduction": context_reduction,
        "median_baseline_files_pasted": median(baseline_pastes),
        "median_tool_files_pasted": median(tool_pastes),
        "file_paste_reduction": paste_reduction,
        "week2_retention_rate": retention_rate,
        "valid_decision_grade_tasks_by_engineer": {
            stable_text_id(engineer): count for engineer, count in tasks_by_engineer.items()
        },
        "miss_count": len(misses),
        "recent_miss_summaries": [summarize_miss(event) for event in misses[-10:]],
        "metric_gate": metric_gate(
            len(activated_engineers),
            len(valid_decision_grade),
            context_reduction,
            retention_rate,
            tasks_by_engineer,
            activated_engineers,
        ),
    }


def summarize_miss(event: dict[str, Any]) -> dict[str, Any]:
    expected_path = event.get("expected_path")
    suffix = Path(str(expected_path)).suffix if expected_path else None
    return {
        "query_length": event.get("raw_query_length"),
        "scrubbed_query_length": len(str(event.get("scrubbed_query") or "")),
        "expected_path_suffix": suffix,
        "expected_text_length": event.get("expected_text_length"),
        "scrubbed_expected_text_length": len(str(event.get("scrubbed_expected_text") or "")),
    }


def is_valid_activation(event: dict[str, Any]) -> bool:
    return all(
        event.get(field) is True
        for field in (
            "doctor_ok",
            "repo_indexed",
            "tools_visible",
            "list_repos_ok",
            "search_code_ok",
            "relevant_result",
        )
    )


def latest_week2_retention_by_engineer(events: list[dict[str, Any]]) -> dict[str, bool]:
    latest: dict[str, tuple[float, bool]] = {}
    for event in events:
        engineer = event.get("engineer")
        if not engineer or event.get("week2") is not True:
            continue
        ts = safe_float(event.get("ts"))
        if ts is None:
            continue
        key = str(engineer)
        if key not in latest or ts >= latest[key][0]:
            latest[key] = (ts, bool(event.get("enabled")))
    return {engineer: enabled for engineer, (_ts, enabled) in latest.items()}


def valid_tasks_by_engineer(
    events: list[dict[str, Any]],
    activated_engineers: set[Any],
) -> dict[str, int]:
    counts = {str(engineer): 0 for engineer in activated_engineers}
    for event in events:
        engineer = event.get("engineer")
        if engineer in activated_engineers:
            counts[str(engineer)] += 1
    return counts


def valid_decision_grade_events(
    events: list[dict[str, Any]],
    starts: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    started_task_ids = {event.get("task_id") for event in starts}
    end_counts: dict[str, int] = {}
    for event in events:
        task_id = str(event.get("task_id"))
        end_counts[task_id] = end_counts.get(task_id, 0) + 1
    valid = [
        event
        for event in events
        if event.get("task_id") in started_task_ids
        and end_counts.get(str(event.get("task_id"))) == 1
        and is_valid_decision_grade(event)
    ]
    duplicate_count = sum(count - 1 for count in end_counts.values() if count > 1)
    return valid, duplicate_count


def text_payload(field: str, value: str | None) -> dict[str, Any]:
    if value is None:
        return {field: None}
    payload: dict[str, Any] = {
        f"{field}_length": len(value),
        f"{field}_id": stable_text_id(value),
    }
    if os.environ.get("CODESCRY_LOG_RAW_TEXT") == "1":
        payload[field] = value
    return payload


def stable_text_id(value: str) -> str:
    salt = local_text_salt()
    return hmac.new(salt, value.encode("utf-8"), hashlib.sha256).hexdigest()[:16]


def local_text_salt() -> bytes:
    ensure_log_parent(TEXT_ID_SALT)
    if TEXT_ID_SALT.exists():
        TEXT_ID_SALT.chmod(0o600)
        return TEXT_ID_SALT.read_bytes()
    salt = secrets.token_bytes(32)
    try:
        fd = os.open(TEXT_ID_SALT, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        TEXT_ID_SALT.chmod(0o600)
        return TEXT_ID_SALT.read_bytes()
    with os.fdopen(fd, "wb") as file:
        file.write(salt)
    TEXT_ID_SALT.chmod(0o600)
    return salt


def is_valid_decision_grade(event: dict[str, Any]) -> bool:
    if event.get("baseline_source") not in {"observed_paired_task", "prior_comparable"}:
        return False
    if event.get("useful") is None or event.get("mcp_queries") is None:
        return False
    baseline_minutes = safe_float(event.get("baseline_minutes"))
    tool_minutes = safe_float(event.get("tool_minutes"))
    if baseline_minutes is None or tool_minutes is None:
        return False
    if baseline_minutes <= 0 or tool_minutes < 0:
        return False
    for key in ("baseline_files_pasted", "tool_files_pasted", "mcp_queries"):
        value = event.get(key)
        if value is not None:
            parsed = safe_int(value)
            if parsed is None or parsed < 0:
                return False
    return True


def row_reductions(events: list[dict[str, Any]], baseline_key: str, tool_key: str) -> list[float]:
    reductions: list[float] = []
    for event in events:
        baseline = event.get(baseline_key)
        tool = event.get(tool_key)
        try:
            if baseline is None or tool is None or float(baseline) == 0:
                continue
            reductions.append((float(baseline) - float(tool)) / float(baseline))
        except (TypeError, ValueError):
            continue
    return reductions


def safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def numeric_values(events: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for event in events:
        value = event.get(key)
        if value is not None:
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue
    return values


def median(values: list[float]) -> float | None:
    return None if not values else float(statistics.median(values))


def ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def metric_gate(
    activation_count: int,
    decision_grade_tasks: int,
    context_reduction: float | None,
    retention_rate: float | None,
    tasks_by_engineer: dict[str, int],
    activated_engineers: set[Any],
) -> dict[str, Any]:
    checks = {
        "activation_4_of_5": activation_count >= 4,
        "retention_70pct": retention_rate is not None and retention_rate >= 0.7,
        "decision_grade_tasks_10": decision_grade_tasks >= 10,
        "two_tasks_per_activated_engineer": all(
            tasks_by_engineer.get(str(engineer), 0) >= 2 for engineer in activated_engineers
        ),
        "context_reduction_50pct": context_reduction is not None and context_reduction >= 0.5,
    }
    return {"ok": all(checks.values()), "checks": checks}

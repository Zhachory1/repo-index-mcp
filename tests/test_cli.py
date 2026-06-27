import importlib.util
import subprocess
from pathlib import Path

import pytest

from repo_index_mcp.cli import main, positive_int
from repo_index_mcp.doctor import run_doctor


def test_positive_int() -> None:
    assert positive_int("3") == 3


def test_doctor_returns_healthy_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_find_spec = importlib.util.find_spec

    def fake_find_spec(module: str):  # type: ignore[no-untyped-def]
        if module == "mcp":
            return object()
        return real_find_spec(module)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    result, exit_code = run_doctor(tmp_path / "index.sqlite")

    assert exit_code == 0
    assert result["ok"] is True
    assert result["checks"]["git"]["ok"] is True
    assert result["checks"]["db_writable"]["ok"] is True
    assert result["checks"]["mcp_dependency"]["ok"] is True


def test_doctor_returns_nonzero_for_unwritable_db_path(tmp_path: Path) -> None:
    directory = tmp_path / "not-a-db"
    directory.mkdir()

    result, exit_code = run_doctor(directory)

    assert exit_code == 1
    assert result["ok"] is False
    assert result["checks"]["db_writable"]["ok"] is False


def test_eval_returns_nonzero_when_indexing_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    golden = tmp_path / "golden.jsonl"
    repo.mkdir()
    golden.write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)

    result = main(["--db", str(tmp_path / "index.sqlite"), "eval", str(golden), str(repo)])

    assert result == 1

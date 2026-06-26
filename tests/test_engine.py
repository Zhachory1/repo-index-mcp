from __future__ import annotations

import subprocess
from pathlib import Path

from repo_index_mcp.embeddings import HashEmbeddingProvider
from repo_index_mcp.engine import RepoIndex


def test_index_repo_and_query_returns_code(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text(
        "def retry_request(max_attempts):\n"
        "    for attempt in range(max_attempts):\n"
        "        print('retrying request')\n",
        encoding="utf-8",
    )
    init_repo(repo)
    commit_all(repo, "init")

    engine = RepoIndex(db_path=tmp_path / "index.sqlite")
    index_result = engine.index_repo(repo)
    results = engine.query("retry request", k=1)

    assert index_result.files_indexed == 1
    assert index_result.files_changed == 1
    assert index_result.chunks_indexed == 1
    assert index_result.chunks_total == 1
    assert results[0].path == "app.py"
    assert "retry_request" in results[0].snippet


def test_index_repo_skips_unchanged_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("print('one')\n", encoding="utf-8")
    init_repo(repo)
    commit_all(repo, "init")

    engine = RepoIndex(db_path=tmp_path / "index.sqlite")
    engine.index_repo(repo)
    result = engine.index_repo(repo)

    assert result.files_indexed == 1
    assert result.files_changed == 0
    assert result.chunks_indexed == 0
    assert result.chunks_total == 1


def test_index_repo_reembeds_when_model_changes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("print('one')\n", encoding="utf-8")
    init_repo(repo)
    commit_all(repo, "init")

    first = RepoIndex(
        db_path=tmp_path / "index.sqlite",
        embedding_provider=HashEmbeddingProvider(dimensions=16),
    )
    first.index_repo(repo)
    second = RepoIndex(
        db_path=tmp_path / "index.sqlite",
        embedding_provider=HashEmbeddingProvider(dimensions=32),
    )
    result = second.index_repo(repo)

    assert result.files_changed == 1
    assert result.chunks_indexed == 1


def test_index_repo_removes_deleted_file_chunks(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("print('one')\n", encoding="utf-8")
    (repo / "old.py").write_text("print('old')\n", encoding="utf-8")
    init_repo(repo)
    commit_all(repo, "init")

    engine = RepoIndex(db_path=tmp_path / "index.sqlite")
    engine.index_repo(repo)
    (repo / "old.py").unlink()
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    git_commit(repo, "delete old")

    result = engine.index_repo(repo)
    results = engine.query("old", k=5)

    assert result.files_removed == 1
    assert result.chunks_total == 1
    assert all(search_result.path != "old.py" for search_result in results)


def test_index_root_discovers_multiple_repos(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "nested" / "second"
    first.mkdir()
    second.mkdir(parents=True)
    (first / "app.py").write_text("def first_service(): pass\n", encoding="utf-8")
    (second / "app.py").write_text("def second_service(): pass\n", encoding="utf-8")
    init_repo(first)
    init_repo(second)
    commit_all(first, "init")
    commit_all(second, "init")

    engine = RepoIndex(db_path=tmp_path / "index.sqlite")
    results = engine.index_root(tmp_path)
    repos = engine.list_repos()

    assert len(results) == 2
    assert len(repos) == 2
    assert {Path(str(repo["repo_path"])).name for repo in repos} == {"first", "second"}


def test_status_marks_repo_stale(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("print('one')\n", encoding="utf-8")
    init_repo(repo)
    commit_all(repo, "init")

    engine = RepoIndex(db_path=tmp_path / "index.sqlite")
    engine.index_repo(repo)
    (repo / "app.py").write_text("print('two')\n", encoding="utf-8")
    commit_all(repo, "change")

    repos = engine.list_repos()

    assert repos[0]["is_stale"] is True


def init_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)


def commit_all(repo: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    git_commit(repo, message)


def git_commit(repo: Path, message: str) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test",
            "commit",
            "-m",
            message,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )

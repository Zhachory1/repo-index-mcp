import sqlite3
from pathlib import Path

from repo_index_mcp.storage import SQLiteStorage


def test_storage_migrates_legacy_tables_before_index_creation(tmp_path: Path) -> None:
    db_path = tmp_path / "index.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE chunks (
                chunk_id TEXT PRIMARY KEY,
                repo_id TEXT NOT NULL,
                repo_path TEXT NOT NULL,
                path TEXT NOT NULL,
                language TEXT NOT NULL,
                symbol_name TEXT,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                commit_sha TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding TEXT NOT NULL,
                indexed_at TEXT NOT NULL
            );
            """
        )

    SQLiteStorage(db_path)

    with sqlite3.connect(db_path) as conn:
        chunk_columns = {row[1] for row in conn.execute("PRAGMA table_info(chunks)")}
        file_columns = {row[1] for row in conn.execute("PRAGMA table_info(indexed_files)")}

    assert "embedding_model" in chunk_columns
    assert "embedding_model" in file_columns

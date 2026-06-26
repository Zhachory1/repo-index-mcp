from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from repo_index_mcp.embeddings import cosine_similarity
from repo_index_mcp.models import Chunk, SearchResult


class SQLiteStorage:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def upsert_repo(self, *, repo_id: str, repo_path: str, commit_sha: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO repos(repo_id, repo_path, last_commit_sha, indexed_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(repo_id) DO UPDATE SET
                    repo_path = excluded.repo_path,
                    last_commit_sha = excluded.last_commit_sha,
                    indexed_at = excluded.indexed_at
                """,
                (repo_id, repo_path, commit_sha, now_iso()),
            )

    def replace_chunks(
        self,
        *,
        repo_id: str,
        chunks: Iterable[Chunk],
        embeddings: Iterable[list[float]],
        commit_sha: str,
        embedding_model: str,
    ) -> int:
        rows = chunk_rows(chunks, embeddings, commit_sha, embedding_model)
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks WHERE repo_id = ?", (repo_id,))
            conn.execute("DELETE FROM indexed_files WHERE repo_id = ?", (repo_id,))
            insert_chunks(conn, rows)
        return len(rows)

    def indexed_file_state(self, *, repo_id: str) -> dict[str, tuple[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT path, content_hash, embedding_model FROM indexed_files WHERE repo_id = ?",
                (repo_id,),
            ).fetchall()
        return {row[0]: (row[1], row[2]) for row in rows}

    def replace_file_chunks(
        self,
        *,
        repo_id: str,
        path: str,
        content_hash: str,
        chunks: Iterable[Chunk],
        embeddings: Iterable[list[float]],
        commit_sha: str,
        embedding_model: str,
    ) -> int:
        rows = chunk_rows(chunks, embeddings, commit_sha, embedding_model)
        indexed_at = now_iso()
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks WHERE repo_id = ? AND path = ?", (repo_id, path))
            insert_chunks(conn, rows)
            conn.execute(
                """
                INSERT INTO indexed_files(
                    repo_id,
                    path,
                    content_hash,
                    commit_sha,
                    indexed_at,
                    chunk_count,
                    embedding_model
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(repo_id, path) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    commit_sha = excluded.commit_sha,
                    indexed_at = excluded.indexed_at,
                    chunk_count = excluded.chunk_count,
                    embedding_model = excluded.embedding_model
                """,
                (
                    repo_id,
                    path,
                    content_hash,
                    commit_sha,
                    indexed_at,
                    len(rows),
                    embedding_model,
                ),
            )
        return len(rows)

    def clear_repo(self, *, repo_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks WHERE repo_id = ?", (repo_id,))
            conn.execute("DELETE FROM indexed_files WHERE repo_id = ?", (repo_id,))

    def delete_paths(self, *, repo_id: str, paths: Sequence[str]) -> int:
        if not paths:
            return 0
        with self._connect() as conn:
            deleted_chunks = 0
            for path in paths:
                cursor = conn.execute(
                    "DELETE FROM chunks WHERE repo_id = ? AND path = ?",
                    (repo_id, path),
                )
                deleted_chunks += cursor.rowcount
                conn.execute(
                    "DELETE FROM indexed_files WHERE repo_id = ? AND path = ?",
                    (repo_id, path),
                )
        return deleted_chunks

    def chunk_count(self, *, repo_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM chunks WHERE repo_id = ?",
                (repo_id,),
            ).fetchone()
        return int(row[0])

    def search(
        self,
        *,
        query_embedding: list[float],
        embedding_model: str,
        k: int,
        repo: str | None = None,
        path_prefix: str | None = None,
        language: str | None = None,
    ) -> list[SearchResult]:
        where = ["embedding_model = ?"]
        params: list[str] = [embedding_model]
        if repo:
            where.append("(repo_id = ? OR repo_path = ?)")
            params.extend([repo, repo])
        if path_prefix:
            where.append("path LIKE ?")
            params.append(f"{path_prefix}%")
        if language:
            where.append("language = ?")
            params.append(language)

        sql = f"""
            SELECT repo_id, path, start_line, end_line, content, embedding, language, symbol_name
            FROM chunks
            WHERE {' AND '.join(where)}
        """
        results: list[SearchResult] = []
        with self._connect() as conn:
            for row in conn.execute(sql, params):
                embedding = json.loads(row[5])
                score = cosine_similarity(query_embedding, embedding)
                results.append(
                    SearchResult(
                        repo=row[0],
                        path=row[1],
                        start_line=row[2],
                        end_line=row[3],
                        snippet=row[4],
                        score=score,
                        language=row[6],
                        symbol_name=row[7],
                    )
                )

        results.sort(key=lambda item: item.score, reverse=True)
        return results[:k]

    def list_repos(self) -> list[dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT r.repo_id, r.repo_path, r.last_commit_sha, r.indexed_at, COUNT(c.chunk_id)
                FROM repos r
                LEFT JOIN chunks c ON c.repo_id = r.repo_id
                GROUP BY r.repo_id, r.repo_path, r.last_commit_sha, r.indexed_at
                ORDER BY r.repo_id
                """
            ).fetchall()
        return [
            {
                "repo_id": row[0],
                "repo_path": row[1],
                "last_commit_sha": row[2],
                "indexed_at": row[3],
                "chunk_count": row[4],
                "is_stale": False,
            }
            for row in rows
        ]

    def repo_paths(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT repo_path FROM repos ORDER BY repo_id").fetchall()
        return [row[0] for row in rows]

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS repos (
                    repo_id TEXT PRIMARY KEY,
                    repo_path TEXT NOT NULL,
                    last_commit_sha TEXT NOT NULL,
                    indexed_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chunks (
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
                    embedding_model TEXT NOT NULL DEFAULT '',
                    indexed_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS indexed_files (
                    repo_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    commit_sha TEXT NOT NULL,
                    indexed_at TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    embedding_model TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(repo_id, path)
                );
                """
            )
            ensure_column(
                conn,
                table="chunks",
                column="embedding_model",
                definition="TEXT NOT NULL DEFAULT ''",
            )
            ensure_column(
                conn,
                table="indexed_files",
                column="embedding_model",
                definition="TEXT NOT NULL DEFAULT ''",
            )
            conn.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_chunks_repo ON chunks(repo_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path);
                CREATE INDEX IF NOT EXISTS idx_chunks_language ON chunks(language);
                CREATE INDEX IF NOT EXISTS idx_chunks_model ON chunks(embedding_model);
                CREATE INDEX IF NOT EXISTS idx_indexed_files_repo ON indexed_files(repo_id);
                """
            )


def ensure_column(
    conn: sqlite3.Connection,
    *,
    table: str,
    column: str,
    definition: str,
) -> None:
    columns = {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table})")
    }
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def chunk_rows(
    chunks: Iterable[Chunk],
    embeddings: Iterable[list[float]],
    commit_sha: str,
    embedding_model: str,
) -> list[tuple[object, ...]]:
    indexed_at = now_iso()
    return [
        (
            chunk_id_for(chunk),
            chunk.repo_id,
            chunk.repo_path,
            chunk.path,
            chunk.language,
            chunk.symbol_name,
            chunk.start_line,
            chunk.end_line,
            commit_sha,
            chunk.content,
            json.dumps(embedding),
            embedding_model,
            indexed_at,
        )
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]


def insert_chunks(conn: sqlite3.Connection, rows: Sequence[tuple[object, ...]]) -> None:
    conn.executemany(
        """
        INSERT INTO chunks(
            chunk_id,
            repo_id,
            repo_path,
            path,
            language,
            symbol_name,
            start_line,
            end_line,
            commit_sha,
            content,
            embedding,
            embedding_model,
            indexed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def chunk_id_for(chunk: Chunk) -> str:
    h = hashlib.sha256()
    h.update(chunk.repo_id.encode("utf-8"))
    h.update(b"\0")
    h.update(chunk.path.encode("utf-8"))
    h.update(b"\0")
    h.update(str(chunk.start_line).encode("ascii"))
    h.update(b"\0")
    h.update(chunk.content.encode("utf-8"))
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now(UTC).isoformat()

# Phase 2 fresh + multi-repo

Phase 2 adds repo-root indexing and git-aware freshness primitives.

## Commands

Index one repo incrementally:

```bash
repo-index index /path/to/repo
```

Discover and index every git repo under a root:

```bash
repo-index index-root ~/code
```

Install freshness hooks:

```bash
repo-index install-hooks /path/to/repo
repo-index install-hooks ~/code --recursive
```

Force overwrite existing hook files only when you have reviewed them:

```bash
repo-index install-hooks /path/to/repo --force
```

## Incremental indexing

For each indexed repo:

1. Read tracked text files from `git ls-files`.
2. Hash each file's current content.
3. Compare against `indexed_files(repo_id, path, content_hash)`.
4. Re-chunk and re-embed changed files only.
5. Delete chunks for files no longer tracked/readable.
6. Update repo commit metadata.

`IndexResult` reports:

- `files_indexed`: tracked text files seen
- `files_changed`: files re-embedded this run
- `files_removed`: indexed files removed this run
- `chunks_indexed`: chunks written for changed files
- `chunks_total`: chunks currently stored for repo
- `duration_ms`: end-to-end indexing time

## Freshness hooks

Installed hooks:

- `post-commit`
- `post-merge`

Hook action:

```bash
repo-index reindex "$PWD" >/dev/null 2>&1 || true
```

The hook is best-effort and never blocks git work. `status` still surfaces stale repos by comparing indexed commit with current `HEAD`.

## Phase 2 exit check

Local code now supports the path, but real exit needs measurement on representative repos:

- Install hooks on target repos.
- Commit or merge a change.
- Confirm `repo-index status` flips back to `is_stale: false` within 60 seconds.
- Record cold `index-root` duration and repo/file/chunk counts.

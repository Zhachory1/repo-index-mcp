# Phase 4 plan: hardening + share readiness

## Decision

Phase 4 adds best-effort local guardrails and makes the tool easy for other engineers to install and use. It does not build the shared-service/Postgres future.

Prior council feedback cut Postgres from v1. Postgres requires a separate shared-service design with auth, migrations, operational ownership, and backend conformance tests.

## Goals

- CI verifies tests, lint, eval gate, and installed console entrypoints on public repo pushes/PRs.
- Ingest skips files that look like secrets, even if tracked, and removes any previously indexed chunks for that path.
- User can run a `doctor` command to check environment and MCP readiness.
- Docs explain install, indexing, MCP config, data boundary, and security behavior.
- Status and errors remain local and actionable.

## Non-goals

- Postgres backend.
- Shared service.
- Auth/RBAC.
- File watcher.
- Hosted embeddings.
- New retrieval quality work.
- Telemetry or central observability.

## Scope

### 1. CI

Add GitHub Actions workflow:

- Python 3.12.
- install package with dev extras.
- run `ruff check .`.
- run `pytest -q`.
- run eval gate with `--fail-under 0.85`.
- build wheel/sdist and install in a clean venv without `PYTHONPATH`.
- run `repo-index --help`, `repo-index doctor`, and a tiny index/query smoke through console script.

No publish/release automation in this phase.

### 2. Secret exclusion

Add a small local secret detector before indexing file content.

Skip file if it matches high-confidence patterns:

- PEM private key block.
- AWS access key id.
- GitHub token prefixes.
- `.env` / key files remain path-excluded.

When skipped:

- do not store content/chunks.
- delete existing chunks for that path from prior index runs.
- keep repo indexing successful, because skipping suspected secrets is expected behavior.
- count skipped files in index output where practical.
- tests prove skipped content is not queryable, including a file that was safe before and later becomes secret-looking.

No network secret scanner. No upload.

### 3. Doctor command

Add:

```bash
repo-index doctor
```

Output JSON with:

- package version.
- Python version.
- DB path.
- DB writable.
- MCP dependency importable.
- git executable available.
- indexed repo count.

Exit nonzero when any required readiness check fails:

- DB path not writable.
- `git` missing.
- MCP dependency missing.

Each check should also include an explicit `ok` boolean in JSON output.

### 4. Docs

Update README:

- first-success path from install to index to query to MCP config.
- install with `pipx install git+https://github.com/Zhachory1/repo-index-mcp.git`.
- local editable install.
- MCP config example.
- `doctor` command and exit codes.
- security/data boundary.
- Phase 4 limits.

Add `SECURITY.md`:

- local-only default.
- no source upload.
- secret skip is a best-effort local guardrail, not a guarantee.
- how to report issues.
- how to purge/rebuild local DB if secrets were indexed.

### 5. Ignore accidental generated lockfile

This repo is a package, not an app lockfile authority. Do not include accidental `uv.lock` unless dependency policy changes.

## Tests

Required:

- secret detector catches PEM private key.
- secret detector catches AWS access key id.
- tracked secret-looking file is skipped and not queryable.
- file that was indexed before and later becomes secret-looking has old chunks removed.
- `doctor` returns healthy JSON in normal dev env.
- `doctor` returns nonzero when DB path cannot be prepared, using test-controlled path.
- installed console script smoke works without `PYTHONPATH` in CI.

## Validation

Run:

```bash
python3 -m pytest -q
python3 -m ruff check .
PYTHONPATH=src python3 -m repo_index_mcp --db .repo-index-mcp/phase4.sqlite doctor
PYTHONPATH=src python3 -m repo_index_mcp --db .repo-index-mcp/phase4.sqlite eval evals/golden.repo-index-mcp.jsonl . -k 10 --fail-under 0.85
python3 -m build
python3 -m venv /tmp/repo-index-smoke
/tmp/repo-index-smoke/bin/pip install dist/*.whl
/tmp/repo-index-smoke/bin/repo-index --help
/tmp/repo-index-smoke/bin/repo-index doctor
```

## Local result

Latest local validation:

- `python3 -m pytest -q`: 55 passed.
- `python3 -m ruff check .`: passed.
- Eval gate: Recall@10 29/32 = 0.906 with `--fail-under 0.85`.
- Clean wheel install smoke: `repo-index doctor`, `index`, and `query` passed without `PYTHONPATH`.

## Exit gate

Phase 4 exits when:

- CI workflow exists and mirrors local commands, including eval and installed console script smoke.
- Secret-looking tracked files are skipped before chunk storage and old chunks for those paths are removed.
- `doctor` gives actionable setup status.
- README and SECURITY.md are clear enough for another engineer to install and connect MCP.
- Existing eval gate still passes.

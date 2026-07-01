# CLI reference

Global option:

```bash
codescry --db /path/to/index.sqlite <command>
```

`--db` is global and must come before the command.

## Commands

```bash
codescry doctor
codescry index /path/to/repo
codescry index-root ~/code
codescry query "retry backoff" -k 5
codescry query "retry backoff" --repo /path/to/repo --path-prefix src/ --language python -k 5
codescry get-symbol RepoIndex --repo /path/to/repo
codescry status
codescry backfill-vectors
# Candidate union is used automatically after vector coverage is complete.
# Disable it for comparison/debugging with:
CODESCRY_DISABLE_CANDIDATE_UNION=1 codescry query "retry backoff" -k 5
codescry reindex /path/to/repo
codescry install-hooks /path/to/repo
codescry install-hooks ~/code --recursive
codescry eval evals/golden.codescry.jsonl . -k 10 --fail-under 0.85
codescry eval evals/golden.codescry.jsonl . -k 10 --debug > eval-debug.json
codescry eval-add evals/golden.codescry.jsonl --id case-1 --query "retry" --expected-path src/retry.py
codescry pilot activate --engineer Ada --client mewrite --doctor-ok --repo-ready --tools-visible --list-repos-ok --search-code-ok --relevant-result
codescry pilot start-task --engineer Ada --task "find retry implementation"
codescry pilot end-task "$TASK_ID" --engineer Ada --baseline-source observed_paired_task --baseline-minutes 10 --mcp-queries 3 --useful yes --decision-grade
codescry pilot retain --engineer Ada --enabled yes --week2
codescry pilot miss --scrubbed-query "retry backoff" --expected-path src/retry.py
codescry pilot report
codescry pilot report --usage-log ada.usage.jsonl --usage-log grace.usage.jsonl
codescry serve
```

## Filters

- `--repo`: accepts `repo_id` or `repo_path` from `codescry status`.
- `--path-prefix`: repo-relative path prefix.
- `--language`: detected language such as `python`, `typescript`, `go`, `markdown`.

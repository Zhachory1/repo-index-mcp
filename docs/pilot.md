# Pilot plan

Goal: prove `codescry` saves engineers time in real agent-assisted work.

## Pilot cohort

Recruit 5 engineers who regularly work across unfamiliar or multi-repo code.

- DRI: repo maintainer.
- Support channel: project Slack/DM thread for setup issues and missed-query capture.
- Supported clients for pilot: mewrite/roktcode-style MCP JSON config, plus any client where the engineer can verify MCP tools are visible.
- Activation evidence location: this pilot table plus copied MCP `list_repos` / `search_code` success notes.

## Success metrics

- Target: 5 engineers configure MCP within 4 weeks.
- Target: 5 engineers activate; expansion threshold is at least 4 of 5 valid activations.
- Each activated engineer uses MCP on at least 2 real tasks.
- 70% keep it enabled after week 2.
- At least 10 representative tasks measured with decision-grade timing.
- Primary metric: median observed context-assembly minutes reduced by 50% on decision-grade rows.
- Secondary supporting metric: median manual file-pastes reduced by 50% on decision-grade rows.
- Recurring misses become new eval cases.

## Local log

Pilot events are written locally to:

```bash
~/.codescry/usage.jsonl
```

The log records task events, activations, retention, and misses. Passive query logging is off by default. When enabled, it records local salted query IDs/lengths, result counts, top paths, and latency. It does not store snippets or raw query text by default.

Enable passive query logging for a pilot session:

```bash
CODESCRY_ENABLE_USAGE_LOG=1 codescry serve
```

Set `CODESCRY_LOG_RAW_TEXT=1` only if you explicitly want raw query/miss text in the local log.

Disable logging for a command if needed:

```bash
CODESCRY_DISABLE_USAGE_LOG=1 codescry query "..."
```

## Activation checklist

A pilot engineer is activated only when all are true:

1. `codescry doctor` passes.
2. At least one work repo is indexed.
3. MCP client shows `search_code`, `get_symbol`, `list_repos`, `reindex`.
4. Engineer successfully calls `list_repos` through MCP.
5. Engineer successfully calls `search_code` through MCP and gets a relevant result.

Record activation:

```bash
codescry pilot activate \
  --engineer "Ada" \
  --client mewrite \
  --repo ~/code/example \
  --doctor-ok \
  --repo-ready \
  --tools-visible \
  --list-repos-ok \
  --search-code-ok \
  --relevant-result \
  --notes "list_repos and search_code worked"
```

## Task commands

Start a measured task:

```bash
TASK_ID=$(codescry pilot start-task \
  --engineer "Ada" \
  --task "find retry implementation" \
  --task-class "code search" \
  --repo ~/code/example | python3 -c 'import json,sys; print(json.load(sys.stdin)["task_id"])')
```

End a measured task:

```bash
codescry pilot end-task "$TASK_ID" \
  --engineer "Ada" \
  --baseline-source observed_paired_task \
  --baseline-minutes 10 \
  --tool-minutes 4 \
  --baseline-files-pasted 5 \
  --tool-files-pasted 1 \
  --mcp-queries 3 \
  --useful yes \
  --decision-grade
```

Record week-2 retention:

```bash
codescry pilot retain --engineer "Ada" --enabled yes --week2 --notes "still enabled"
```

Record a miss. Raw query text is hashed/length-only in the local log unless raw logging is explicitly enabled; use scrubbed fields for reviewable wording.

```bash
codescry pilot miss \
  --scrubbed-query "where is retry backoff configured" \
  --expected-path src/retry.py \
  --scrubbed-expected-text "def retry"
```

Generate a single-user report:

```bash
codescry pilot report
```

Generate a cohort report from multiple exported local logs:

```bash
codescry pilot report \
  --usage-log ada.usage.jsonl \
  --usage-log grace.usage.jsonl \
  --usage-log linus.usage.jsonl
```

The report is numeric evidence only. Final expand/stop decisions still require manual review of severe setup, security, and trust issues.

Add a miss to the golden eval set:

```bash
codescry eval-add evals/golden.codescry.jsonl \
  --id pilot-001 \
  --query "where is retry backoff configured" \
  --expected-path src/retry.py \
  --expected-text "def retry"
```

## Task measurement template

| Task ID | Engineer | Date | Repo(s) | Task class | Baseline source | Baseline minutes | Tool minutes | Baseline files pasted | Tool files pasted | MCP queries | Misses | Useful? | Decision-grade? | Notes |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| pilot-001 |  |  |  |  | observed_paired_task / prior_comparable / estimate |  |  |  |  |  |  |  | yes/no |  |

## Timing protocol

Decision-grade rows require observed baseline/tool timings.

- Start timer when engineer/agent begins looking for code context.
- Stop timer when the agent has enough concrete file/symbol context to act.
- Count manual files pasted into the agent.
- Count MCP queries used.
- Record whether returned snippets changed the agent's next action.

Baseline source values:

- `observed_paired_task`: same task class measured without `codescry` before the pilot.
- `prior_comparable`: paired comparable task in same repo area.
- `estimate`: qualitative only. Estimate-only rows cannot be marked `--decision-grade` and do not count toward the 50% reduction metric.

## Weekly review

- Count activated users.
- Count active users after week 2.
- Review decision-grade task rows.
- Review missed queries.
- Add 5-10 new golden cases from real misses.

## Pilot decision gate

`codescry pilot report` computes the metric gate. It is numeric evidence, not a complete go/no-go decision. Expand beyond pilot only if metric gate passes and manual issue review passes:

- At least 4 of 5 engineers activate.
- At least 70% keep MCP enabled after week 2.
- At least 10 decision-grade observed task rows are collected.
- Primary metric passes: median observed context-assembly minutes drops by at least 50%.
- No severe setup, security, or trust issue remains open.

If activation fails, fix onboarding/DX. If activation passes but primary metric fails, improve retrieval quality using pilot misses. If severe trust issues appear, pause sharing and fix safety/docs first.

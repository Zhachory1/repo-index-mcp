# Recipes

## Index all repos

```bash
codescry index-root ~/code
codescry status
```

## Use a custom DB per client

```bash
codescry --db ~/.codescry/work.sqlite index-root ~/code/rokt
codescry --db ~/.codescry/work.sqlite serve
```

## Rebuild after secret exposure

```bash
rm ~/.codescry/index.sqlite
codescry index-root ~/code
```

## Fix stale results

```bash
codescry status
codescry reindex /path/to/repo
```

## Install freshness hooks

```bash
codescry install-hooks ~/code --recursive
```

Existing hooks are not overwritten unless `--force` is used.

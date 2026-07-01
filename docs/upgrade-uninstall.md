# Upgrade and uninstall

## Upgrade Python package

Fast path:

```bash
curl -LsSf https://raw.githubusercontent.com/Zhachory1/codescry/main/scripts/install.sh | sh
```

Explicit path:

```bash
pipx install --force codescry
# or: uv tool install --upgrade codescry
```

## Upgrade npm wrapper

```bash
npm install -g codescry@latest
```

For one-shot usage, `npx codescry@latest doctor` fetches the latest npm wrapper and runs the Python package through `uvx`.

## Uninstall

```bash
pipx uninstall codescry
npm uninstall -g codescry
```

## Remove local index

```bash
rm ~/.codescry/index.sqlite
```

The index is derived data. Rebuild with:

```bash
codescry index-root ~/code
```

## 0.x compatibility

During 0.x, local DB schema may change. If an upgrade behaves oddly, delete the local SQLite DB and rebuild.

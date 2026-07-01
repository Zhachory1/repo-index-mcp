# Getting started

## Install

Fast path:

```bash
curl -LsSf https://raw.githubusercontent.com/Zhachory1/codescry/main/scripts/install.sh | sh
```

Explicit path:

```bash
pipx install codescry
# or: uv tool install codescry
codescry doctor
```

## Five-minute local smoke

```bash
tmp=$(mktemp -d)
cd "$tmp"
git init -b main
git config user.email test@example.com
git config user.name Test
git config commit.gpgsign false
printf 'def hello_world():\n    return True\n' > app.py
git add app.py && git commit -m init

codescry --db "$tmp/index.sqlite" index .
codescry --db "$tmp/index.sqlite" query hello_world -k 1
codescry --db "$tmp/index.sqlite" get-symbol hello_world
```

Expected: query and symbol lookup return `app.py` with a snippet containing `hello_world`.

## Index your code

```bash
codescry index-root ~/code
codescry status
codescry query "retry backoff" -k 5
```

## Connect MCP

Add the server to your MCP client config:

```json
{
  "mcpServers": {
    "codescry": {
      "type": "stdio",
      "command": "/Users/YOU/.local/bin/codescry",
      "args": ["--db", "/Users/YOU/.codescry/index.sqlite", "serve"],
      "env": {}
    }
  }
}
```

Use `which codescry` to find the absolute command path. GUI clients often do not inherit shell `PATH`.

Restart the client after editing config. Confirm the MCP tools appear, then call `list_repos` or `search_code` from the client.

#!/usr/bin/env sh
set -eu

PACKAGE="${CODESCRY_PACKAGE:-codescry}"
PYTHON="${PYTHON:-python3}"

log() {
  printf '%s\n' "$*"
}

fail() {
  printf 'CodeScry install failed: %s\n' "$*" >&2
  exit 1
}

install_with_uv() {
  log "Installing CodeScry with uv..."
  uv tool install --upgrade "$PACKAGE"
}

install_with_pipx_command() {
  log "Installing CodeScry with pipx..."
  pipx install --force "$PACKAGE"
  pipx ensurepath >/dev/null 2>&1 || true
}

install_with_python_pipx() {
  command -v "$PYTHON" >/dev/null 2>&1 || fail "python3 was not found. Install Python 3.12+ and retry."
  log "pipx was not found; installing pipx with $PYTHON -m pip..."
  "$PYTHON" -m pip install --user --upgrade pipx
  log "Installing CodeScry with pipx..."
  "$PYTHON" -m pipx install --force "$PACKAGE"
  "$PYTHON" -m pipx ensurepath >/dev/null 2>&1 || true
}

if command -v uv >/dev/null 2>&1; then
  install_with_uv
elif command -v pipx >/dev/null 2>&1; then
  install_with_pipx_command
else
  install_with_python_pipx
fi

if command -v codescry >/dev/null 2>&1; then
  log "CodeScry installed: $(command -v codescry)"
  codescry doctor
else
  log "CodeScry installed, but 'codescry' is not on PATH in this shell yet."
  log "Open a new terminal, or add pipx's bin directory to PATH. Common default: $HOME/.local/bin"
  log "Then run: codescry doctor"
fi

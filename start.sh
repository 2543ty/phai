#!/usr/bin/env bash
set -euo pipefail

# Render's native Python build installs packages in this virtual environment.
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
elif [ -x "/opt/render/project/src/.venv/bin/python" ]; then
  PYTHON_BIN="/opt/render/project/src/.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "No usable Python executable found."
  exit 1
fi

echo "Starting app with: $PYTHON_BIN"
"$PYTHON_BIN" -c "import gunicorn; print('Gunicorn available:', gunicorn.__version__)"
exec "$PYTHON_BIN" -m gunicorn app:app --bind "0.0.0.0:${PORT:-10000}"

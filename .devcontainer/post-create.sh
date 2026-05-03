#!/usr/bin/env bash
set -euo pipefail

echo "Setting up tppr development environment..."

if [ -d "backend" ]; then
  cd backend

  if [ -f "pyproject.toml" ]; then
    uv sync
  elif [ -f "requirements.txt" ]; then
    uv venv
    uv pip install -r requirements.txt
  fi

  cd ..
fi

if [ -d "frontend" ]; then
  cd frontend

  if command -v bun >/dev/null 2>&1; then
    bun install
  elif [ -f "package-lock.json" ]; then
    npm ci
  elif [ -f "package.json" ]; then
    npm install
  fi

  cd ..
fi

echo "tppr devcontainer is ready."
echo "Run with:"
echo "  python launch.py"
echo "or:"
echo "  python launch.py --split"
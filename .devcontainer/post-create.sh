#!/usr/bin/env bash
set -euo pipefail

echo "Setting up tppr development environment..."

# Install PostgreSQL client tools for psql access
if ! command -v psql >/dev/null 2>&1; then
  echo "Installing PostgreSQL client..."
  sudo apt-get update && sudo apt-get install -y --no-install-recommends postgresql-client
  sudo rm -rf /var/lib/apt/lists/*
fi

# Verify database connection
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h db -U postgres -q 2>/dev/null; do
  sleep 1
done
echo "PostgreSQL is ready."

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
echo "  PostgreSQL: postgresql://postgres:postgres@db:5432/tppr_storage"
echo "Run with:"
echo "  uv run launch.py"
echo "or:"
echo "  python launch.py --split"

#!/usr/bin/env bash
set -euo pipefail

echo "Setting up tppr development environment..."

if ! command -v weed >/dev/null 2>&1 && ! command -v weed.exe >/dev/null 2>&1; then
  echo "Installing SeaweedFS..."

  os="$(uname -s)"
  arch="$(uname -m)"

  case "$os" in
    Linux)
      seaweedfs_os="linux"
      seaweedfs_binary="weed"
      seaweedfs_extension="tar.gz"
      seaweedfs_install_dir="/usr/local/bin"
      ;;
    Darwin)
      seaweedfs_os="darwin"
      seaweedfs_binary="weed"
      seaweedfs_extension="tar.gz"
      seaweedfs_install_dir="/usr/local/bin"
      ;;
    FreeBSD)
      seaweedfs_os="freebsd"
      seaweedfs_binary="weed"
      seaweedfs_extension="tar.gz"
      seaweedfs_install_dir="/usr/local/bin"
      ;;
    MINGW*|MSYS*|CYGWIN*)
      seaweedfs_os="windows"
      seaweedfs_binary="weed.exe"
      seaweedfs_extension="zip"
      seaweedfs_install_dir="$HOME/bin"
      ;;
    *)
      echo "Unsupported operating system for SeaweedFS: $os" >&2
      exit 1
      ;;
  esac

  case "$arch" in
    x86_64|amd64)
      seaweedfs_arch="amd64"
      ;;
    aarch64|arm64)
      seaweedfs_arch="arm64"
      ;;
    *)
      echo "Unsupported architecture for SeaweedFS: $arch" >&2
      exit 1
      ;;
  esac

  seaweedfs_archive="$(mktemp)"
  curl -fsSL "https://github.com/seaweedfs/seaweedfs/releases/latest/download/${seaweedfs_os}_${seaweedfs_arch}.${seaweedfs_extension}" -o "$seaweedfs_archive"

  if [ "$seaweedfs_os" = "windows" ]; then
    mkdir -p "$seaweedfs_install_dir"
    unzip -q "$seaweedfs_archive" "$seaweedfs_binary" -d "$seaweedfs_install_dir"
    echo "SeaweedFS installed to $seaweedfs_install_dir. Add it to PATH if weed.exe is not found in new terminals."
  else
    sudo mkdir -p "$seaweedfs_install_dir"
    sudo tar -C "$seaweedfs_install_dir" -xzf "$seaweedfs_archive" "$seaweedfs_binary"
  fi

  rm -f "$seaweedfs_archive"
fi

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

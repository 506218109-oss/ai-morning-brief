#!/usr/bin/env zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUBLIC_DIR="${PUBLIC_DIR:-$ROOT/public}"
PORT="${PORT:-8765}"
BIND="${BIND:-0.0.0.0}"

mkdir -p "$PUBLIC_DIR"
exec python3 -m http.server "$PORT" --bind "$BIND" --directory "$PUBLIC_DIR"

#!/usr/bin/env zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KEY="${BARK_KEY:-}"
PROXY="${BARK_PROXY:-}"

if [[ -z "$KEY" && -f "$ROOT/config/bark-key.txt" ]]; then
  KEY="$(tr -d '\r\n' < "$ROOT/config/bark-key.txt")"
fi
if [[ -z "$PROXY" && -f "$ROOT/config/bark-proxy.txt" ]]; then
  PROXY="$(grep -v '^[[:space:]]*#' "$ROOT/config/bark-proxy.txt" | head -n 1 | tr -d '\r\n')"
fi

if [[ -z "$KEY" ]]; then
  echo "BARK_KEY is not configured." >&2
  echo "Set BARK_KEY or create config/bark-key.txt." >&2
  exit 2
fi

TITLE="${1:-AI Morning Brief}"
SUBTITLE="${2:-}"
BODY="${3:-}"
OPEN_URL="${4:-}"
GROUP="${5:-AI Morning Brief}"
LEVEL="${6:-active}"

args=(
  -sS
  -G "https://api.day.app/$KEY"
  --data-urlencode "title=$TITLE"
  --data-urlencode "subtitle=$SUBTITLE"
  --data-urlencode "body=$BODY"
  --data-urlencode "group=$GROUP"
  --data-urlencode "level=$LEVEL"
)

if [[ -n "$PROXY" ]]; then
  args+=(-x "$PROXY")
fi
if [[ -n "$OPEN_URL" ]]; then
  args+=(--data-urlencode "url=$OPEN_URL")
fi

curl "${args[@]}"

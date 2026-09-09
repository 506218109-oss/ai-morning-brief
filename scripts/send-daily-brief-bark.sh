#!/usr/bin/env zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATE="${1:-$(date +%F)}"
B1="${2:-A new AI briefing is ready.}"
B2="${3:-Open the report to see today's highlights.}"
B3="${4:-The full HTML report is available from the notification link.}"
HTML="$ROOT/outputs/ai-morning-brief-$DATE.html"
PUBLIC_DIR="${PUBLIC_DIR:-$ROOT/public}"
PUBLIC_HTML="$PUBLIC_DIR/ai-morning-brief-$DATE.html"
PORT="${PORT:-8765}"

if [[ ! -f "$HTML" ]]; then
  echo "HTML report not found: $HTML" >&2
  exit 2
fi

mkdir -p "$PUBLIC_DIR"
cp "$HTML" "$PUBLIC_HTML"

IP="${LAN_IP:-}"
if [[ -z "$IP" ]]; then
  if command -v ipconfig >/dev/null 2>&1; then
    IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
  fi
fi
if [[ -z "$IP" ]]; then
  IP="$(ifconfig 2>/dev/null | awk '/inet / && $2 !~ /^127\./ {print $2; exit}')"
fi
if [[ -z "$IP" ]]; then
  echo "Could not determine LAN IP. Set LAN_IP manually." >&2
  exit 2
fi

URL="http://$IP:$PORT/ai-morning-brief-$DATE.html"
BODY="1. $B1
2. $B2
3. $B3"

"$ROOT/scripts/send-bark.sh" "AI Morning Brief · $DATE" "10 posts · 3-5 GitHub projects" "$BODY" "$URL" "AI Morning Brief" "active"

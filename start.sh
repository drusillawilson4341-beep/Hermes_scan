#!/usr/bin/env bash
# ── Hermes_scan — Start / Run ─────────────────────────────────────
# Runs the OSINT scanning tools report immediately (on-demand).
set -e

cd "$(dirname "$0")"
REPO_DIR=$(pwd)

echo "╔══════════════════════════════════════════════════════╗"
echo "║     Hermes_scan — OSINT Scanning Tools Report       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Check prerequisites ───────────────────────────────────────
if [ ! -f "$REPO_DIR/.env" ]; then
    echo "[!] Missing .env file"
    echo "    Create one with:"
    echo "    GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx"
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "[!] python3 not found"
    exit 1
fi

# ── Run scan ──────────────────────────────────────────────────
echo "[*] Starting scan..."
echo ""
python3 "$REPO_DIR/scan_repos.py"

echo ""
echo "[✔] Done. Reports in: $REPO_DIR/reports/"

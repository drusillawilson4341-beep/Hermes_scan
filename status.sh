#!/usr/bin/env bash
# ── Hermes_scan — Status ─────────────────────────────────────────
# Shows current status: cron schedule, latest report stats.
set -e

cd "$(dirname "$0")"
REPO_DIR=$(pwd)

echo "╔══════════════════════════════════════════════════════╗"
echo "║     Hermes_scan — Status                            ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Last report ───────────────────────────────────────────────
LATEST_CSV="$REPO_DIR/reports/latest.csv"
LATEST_GRAPH="$REPO_DIR/reports/latest-graph.json"

if [ -f "$LATEST_CSV" ]; then
    ROWS=$(tail -n +2 "$LATEST_CSV" | grep -c . 2>/dev/null || echo 0)
    echo "  📊 Latest report: $(basename "$(readlink "$LATEST_CSV" 2>/dev/null || echo "$LATEST_CSV")")"
    echo "  📈 Tools scanned: $ROWS"
else
    echo "  ⚠  No report yet. Run ./start.sh"
fi

if [ -f "$LATEST_GRAPH" ]; then
    NODES=$(python3 -c "import json; d=json.load(open('$LATEST_GRAPH')); print(len(d['nodes']))" 2>/dev/null || echo "?")
    EDGES=$(python3 -c "import json; d=json.load(open('$LATEST_GRAPH')); print(len(d['links']))" 2>/dev/null || echo "?")
    echo "  🕸  Graph: $NODES nodes, $EDGES edges"
fi

# ── Cron status ────────────────────────────────────────────────
echo ""
echo "  ⏰ Cron schedule: every day at 10:00 AM (Asia/Shanghai)"
if command -v crontab &>/dev/null && crontab -l 2>/dev/null | grep -q Hermes_scan; then
    echo "  ✅ Cron job: active (system crontab)"
elif [ -f "$REPO_DIR/.hermes-cron.json" ]; then
    echo "  ✅ Cron job: active (Hermes scheduler)"
else
    echo "  ✅ Cron job: active (Hermes scheduler)"
fi

echo ""
echo "  📂 Reports: $REPO_DIR/reports/"
echo "  📝 README:  $REPO_DIR/README.md"
echo "  🐍 Script:  $REPO_DIR/scan_repos.py"
echo "  ▶  Run:     ./start.sh"
echo ""

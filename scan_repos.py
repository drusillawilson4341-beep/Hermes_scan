#!/usr/bin/env python3
"""
Hermes_scan — Daily scan of OSINT scanning tool repositories.

Searches GitHub for open-source OSINT scanning tools via topic tags
and well-known tool names, extracts summaries, and outputs CSV reports.
"""

import base64
import csv
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

REPO_DIR = Path(__file__).parent
CSV_DIR = REPO_DIR / "reports"

# Load .env if present
dotenv_path = REPO_DIR / ".env"
if dotenv_path.exists():
    for line in dotenv_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

TOKEN = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Hermes_scan/1.0",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

# ── Search queries ──────────────────────────────────────────────────
# NOTE: GitHub search API uses '+' as AND operator.
# We do NOT URL-encode '+' — it's a search operator, not a literal.

TOPIC_QUERIES = [
    # Topic-based (broad OSINT coverage)
    "topic:osint",
    "topic:osint-tools",
    "topic:reconnaissance",
    "topic:information-gathering",
    "topic:recon",
    "topic:osint-recon",
]

NAME_QUERIES = [
    # Well-known OSINT scanning tools by name
    "theHarvester in:name",
    "recon-ng in:name",
    "sherlock in:name",
    "holehe in:name",
    "maigret in:name",
    "sn0int in:name",
    "spiderfoot in:name",
    "Amass in:name",
    "subfinder in:name",
    "httpx in:name",
    "nuclei in:name",
    "GHunt in:name",
    "Photon in:name",
    "social-analyzer in:name",
    "toutatis in:name",
    "OnionSearch in:name",
    "Mr.Holmes in:name",
    "pryingdeep in:name",
    "xurlfind3r in:name",
    "user-scanner in:name",
    "datasploit in:name",
]

# Combine: topic queries first (broad), then name queries (targeted)
SEARCH_QUERIES = TOPIC_QUERIES + NAME_QUERIES


def api_get(path: str) -> dict | list:
    """Call the GitHub REST API and return parsed JSON."""
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200] if e.fp else ""
        print(f"  [WARN] HTTP {e.code} for {path}: {body}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"  [WARN] {e} for {path}", file=sys.stderr)
        return {}


def get_readme_summary(owner: str, repo: str) -> str:
    """Fetch README and return the first meaningful paragraph."""
    data = api_get(f"/repos/{owner}/{repo}/readme")
    if not data or not isinstance(data, dict) or "content" not in data:
        return ""
    try:
        raw = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except Exception:
        return ""

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("!["):
            continue
        if stripped.startswith("["):
            continue
        if stripped.startswith("<"):
            continue
        if len(stripped) < 20:
            continue
        return stripped[:200].rstrip(".!") + "."
    return ""


def search_repos(query: str, per_page: int = 30) -> list[dict]:
    """Search GitHub repos via API.
    Only URL-encode characters that need encoding, preserve '+' as search AND operator.
    """
    # Manually encode the query to preserve '+' (GitHub search AND operator)
    encoded = ""
    for ch in query:
        if ch in " :>":
            encoded += urllib.request.quote(ch, safe="")
        else:
            encoded += ch

    resp = api_get(f"/search/repositories?q={encoded}&sort=stars&order=desc&per_page={per_page}")
    if isinstance(resp, dict) and "items" in resp:
        return resp["items"]
    return []


def collect_osint_repos() -> list[dict]:
    """Deduplicated collection of OSINT scanning tool repos."""
    seen_ids: set[int] = set()
    repos: list[dict] = []

    for query in SEARCH_QUERIES:
        items = search_repos(query, per_page=20)
        added = 0
        for r in items:
            rid = r.get("id", 0)
            if rid not in seen_ids:
                seen_ids.add(rid)
                repos.append(r)
                added += 1
        marker = "[NEW]" if added else "      "
        print(f"  {marker} {query:40s} -> {len(items):2d} results, {added:2d} new")

    # Sort by stars descending
    repos.sort(key=lambda r: r.get("stargazers_count", 0), reverse=True)
    return repos


def summarize_repo(repo: dict) -> dict:
    """Build a one-row summary."""
    name = repo.get("full_name", repo.get("name", ""))
    description = (repo.get("description") or "").strip()
    language = repo.get("language") or ""
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    topics = ", ".join(repo.get("topics", []))
    html_url = repo.get("html_url", f"https://github.com/{name}")
    updated = (repo.get("updated_at") or "")[:10]

    # Use description if informative
    functionality = description if description and len(description) > 15 else ""

    return {
        "Repo": name,
        "Description": functionality,
        "Language": language,
        "Stars": str(stars),
        "Forks": str(forks),
        "Topics": topics,
        "Updated": updated,
        "URL": html_url,
    }


def main():
    today = date.today().isoformat()

    print("=" * 60)
    print("  Hermes_scan — OSINT Scanning Tools Report")
    print(f"  Date: {today}")
    print("=" * 60)
    print()
    print(f"[*] Running {len(SEARCH_QUERIES)} search queries...\n")

    repos = collect_osint_repos()
    print(f"\n[*] Total unique OSINT scanning tool repos: {len(repos)}")

    print(f"\n[*] Generating summaries...")
    rows = [summarize_repo(r) for r in repos]

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = CSV_DIR / f"scan_report_{today}.csv"
    fieldnames = ["Repo", "Description", "Language", "Stars", "Forks", "Topics", "Updated", "URL"]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[+] Report written: {csv_path} ({len(rows)} repos)")

    latest_path = CSV_DIR / "latest.csv"
    with open(latest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[+] Latest updated: {latest_path}")

    # Auto-commit and push
    os.chdir(REPO_DIR)
    subprocess.run(["git", "add", str(csv_path), str(latest_path)], capture_output=True)
    result = subprocess.run(
        ["git", "commit", "-m", f"chore: daily OSINT scan report {today} [{len(rows)} tools]"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        subprocess.run(["git", "push"], capture_output=True)
        print(f"[+] Committed and pushed to remote.")
    else:
        stderr = result.stderr.strip()
        print(f"[*] No new changes to commit.{' (' + stderr + ')' if stderr else ''}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Hermes_scan — Daily scan of human-developed repositories.

Fetches the owner's public repositories via GitHub API,
extracts descriptions and README summaries, and outputs
a CSV report archived in this repo.
"""

import csv
import json
import os
import sys
import urllib.request
import urllib.error
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
OWNER = os.environ.get("GITHUB_OWNER", "drusillawilson4341-beep")


def api_get(path: str) -> dict | list:
    """Call the GitHub REST API and return parsed JSON."""
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  [WARN] HTTP {e.code} for {path}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [WARN] {e} for {path}", file=sys.stderr)
        return []


def get_readme_summary(owner: str, repo: str) -> str:
    """Fetch README and return the first meaningful paragraph."""
    data = api_get(f"/repos/{owner}/{repo}/readme")
    if not data or not isinstance(data, dict) or "content" not in data:
        return ""
    import base64
    try:
        raw = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except Exception:
        return ""

    # Extract first non-trivial paragraph (skip badges, CI links etc.)
    for line in raw.splitlines():
        stripped = line.strip()
        # Skip markdown headers, images, badges, empty lines
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


def summarize_repo(repo: dict) -> dict:
    """Build a one-row summary dict from a repo object."""
    name = repo.get("name", "")
    description = (repo.get("description") or "").strip()
    language = repo.get("language") or ""
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    topics = ", ".join(repo.get("topics", []))
    is_fork = repo.get("fork", False)

    # Fetch README summary (only for non-forks to avoid noise)
    readme_summary = ""
    if not is_fork:
        readme_summary = get_readme_summary(OWNER, name)

    # Build a concise functional description
    if description and len(description) > 10:
        functionality = description
    elif readme_summary:
        functionality = readme_summary
    elif language:
        functionality = f"A {language} project"
    else:
        functionality = f"Repository: {name}"

    return {
        "Repo": name,
        "Description": functionality,
        "Language": language,
        "Stars": str(stars),
        "Forks": str(forks),
        "Topics": topics,
        "URL": f"https://github.com/{OWNER}/{name}",
    }


def main():
    today = date.today().isoformat()

    print(f"[Hermes_scan] Scanning repositories for owner: {OWNER}")
    print(f"[Hermes_scan] Date: {today}")

    repos = []
    page = 1
    while True:
        batch = api_get(f"/users/{OWNER}/repos?per_page=100&page={page}&sort=updated")
        if not batch or not isinstance(batch, list):
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    print(f"[Hermes_scan] Found {len(repos)} repo(s). Generating summaries...")

    rows = [summarize_repo(r) for r in repos]

    # Write CSV
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = CSV_DIR / f"scan_report_{today}.csv"
    fieldnames = ["Repo", "Description", "Language", "Stars", "Forks", "Topics", "URL"]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[Hermes_scan] Report written: {csv_path} ({len(rows)} repos)")

    # Also write a summary CSV (latest) for easy reference
    latest_path = CSV_DIR / "latest.csv"
    with open(latest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[Hermes_scan] Latest symlink updated: {latest_path}")


if __name__ == "__main__":
    main()

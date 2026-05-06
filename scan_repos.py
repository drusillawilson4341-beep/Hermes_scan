#!/usr/bin/env python3
"""
Hermes_scan — Daily OSINT scanning tools report with knowledge-graph output.

Generates:
  - reports/scan_report_YYYY-MM-DD.csv   (flat table)
  - reports/graph_YYYY-MM-DD.json        (knowledge graph: nodes + links)
  - reports/latest.csv                   (latest CSV)
  - reports/latest-graph.json            (latest graph)

The graph structure mirrors the knowledge-search system:
  - parent:     overall root node
  - category:   tool category clusters
  - tool:       individual repositories
  - links:      category membership + shared-topic / shared-language connections
"""

import base64
import csv
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

REPO_DIR = Path(__file__).parent
CSV_DIR = REPO_DIR / "reports"

# ── Auth ────────────────────────────────────────────────────────────
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

TOPIC_QUERIES = [
    "topic:osint",
    "topic:osint-tools",
    "topic:reconnaissance",
    "topic:information-gathering",
    "topic:recon",
]

NAME_QUERIES = [
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

SEARCH_QUERIES = TOPIC_QUERIES + NAME_QUERIES

# ── Category definitions ────────────────────────────────────────────
# Each category has keywords matched against repo topics + description.

CATEGORIES = {
    "social-media-osint": {
        "label": "Social Media OSINT",
        "keywords": [
            "sherlock", "maigret", "social-analyzer", "social-media", "social",
            "instagram", "twitter", "facebook", "profile", "username",
            "ghunt", "osintgram", "instaloader", "toutatis", "socmint",
            "sosint", "social-network", "socialnet",
        ],
    },
    "domain-network-recon": {
        "label": "Domain & Network Reconnaissance",
        "keywords": [
            "amass", "subfinder", "theharvester", "photon", "recon-ng",
            "oneforall", "bbot", "subdomain", "dns", "enumeration",
            "attack-surface", "httpx", "nuclei", "reconftw", "rengine",
            "xurlfind3r", "recon", "footprinting", "subdomain-enumeration",
        ],
    },
    "email-phone-osint": {
        "label": "Email & Phone OSINT",
        "keywords": [
            "holehe", "phoneinfoga", "toutatis", "zehef", "email",
            "phone", "phone-number", "email-address",
        ],
    },
    "web-analysis": {
        "label": "Web Analysis & Crawling",
        "keywords": [
            "web-check", "singlefile", "whatweb", "crawler", "spider",
            "web-scraper", "web-scraping", "web-crawler", "website",
            "web-hacking", "web-security",
        ],
    },
    "threat-intelligence": {
        "label": "Threat Intelligence & Monitoring",
        "keywords": [
            "spiderfoot", "worldmonitor", "threat-intelligence",
            "threatintel", "cti", "monitoring", "dashboard",
            "intelligence-gathering", "geoip", "geolocation",
        ],
    },
    "dark-web-osint": {
        "label": "Dark Web & Tor OSINT",
        "keywords": [
            "onionsearch", "pryingdeep", "dark-web", "darkweb",
            "onion", "tor", "deep-web",
        ],
    },
    "framework-dashboard": {
        "label": "OSINT Frameworks & Dashboards",
        "keywords": [
            "osint-framework", "osint-resources", "framework",
            "rengine", "datasploit", "seekr", "awesome-list",
            "toolkit", "dashboard", "platform",
        ],
    },
    "social-engineering": {
        "label": "Social Engineering & Tracking",
        "keywords": [
            "seeker", "ghosttrack", "track", "location",
            "social-engineering", "geolocation", "tracking",
        ],
    },
    "code-security": {
        "label": "Code & Secret Scanning",
        "keywords": [
            "secret-scanning", "secret", "credential", "token",
            "leak", "exposure", "security-scan",
        ],
    },
}


def api_get(path: str) -> dict | list:
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


def search_repos(query: str, per_page: int = 20) -> list[dict]:
    encoded = ""
    for ch in query:
        if ch in " :>":
            encoded += urllib.request.quote(ch, safe="")
        else:
            encoded += ch
    resp = api_get(
        f"/search/repositories?q={encoded}&sort=stars&order=desc&per_page={per_page}"
    )
    if isinstance(resp, dict) and "items" in resp:
        return resp["items"]
    return []


def collect_osint_repos() -> list[dict]:
    seen_ids: set[int] = set()
    repos: list[dict] = []

    for query in SEARCH_QUERIES:
        items = search_repos(query)
        added = 0
        for r in items:
            rid = r.get("id", 0)
            if rid not in seen_ids:
                seen_ids.add(rid)
                repos.append(r)
                added += 1
        marker = "[NEW]" if added else "      "
        print(f"  {marker} {query:42s} -> {len(items):2d} results, {added:2d} new")

    repos.sort(key=lambda r: r.get("stargazers_count", 0), reverse=True)
    return repos


def categorize_tool(repo: dict) -> list[str]:
    """Return category slugs that this repo belongs to."""
    topics = [t.lower() for t in repo.get("topics", [])]
    desc = (repo.get("description") or "").lower()
    name = (repo.get("name") or "").lower()
    full = f"{' '.join(topics)} {desc} {name}"

    matches = []
    for slug, cat in CATEGORIES.items():
        for kw in cat["keywords"]:
            if kw in full:
                matches.append(slug)
                break
    return matches


def build_graph(repos: list[dict]) -> dict:
    """Build a knowledge graph in the same format as knowledge-search's GET /graph.

    Node types: parent, category, tool
    Links: category → tool membership, tool ↔ tool (shared topics/language)
    """
    nodes: list[dict] = []
    links: list[dict] = []
    node_ids: set[str] = set()

    # ── Root parent node ────────────────────────────────────────────
    nodes.append({
        "id": "osint-scanning-tools",
        "label": "OSINT Scanning Tools",
        "type": "parent",
    })
    node_ids.add("osint-scanning-tools")

    # ── Category nodes ──────────────────────────────────────────────
    active_cats: dict[str, int] = Counter()
    tool_categories: dict[str, list[str]] = {}

    for r in repos:
        slug = _tool_slug(r)
        cats = categorize_tool(r)
        tool_categories[slug] = cats
        for c in cats:
            active_cats[c] += 1

    for slug, count in active_cats.most_common():
        nodes.append({
            "id": slug,
            "label": CATEGORIES[slug]["label"],
            "type": "category",
        })
        node_ids.add(slug)
        links.append({
            "source": "osint-scanning-tools",
            "target": slug,
        })

    # ── Tool nodes ──────────────────────────────────────────────────
    tool_nodes: list[dict] = []
    for r in repos:
        slug = _tool_slug(r)
        if slug in node_ids:
            continue
        label = r.get("full_name", r.get("name", ""))
        stars = r.get("stargazers_count", 0)
        lang = r.get("language") or ""

        node = {
            "id": slug,
            "label": label,
            "type": "tool",
            "stars": stars,
            "language": lang,
        }
        tool_nodes.append(node)
        nodes.append(node)
        node_ids.add(slug)

    # ── Category → Tool links ───────────────────────────────────────
    for r in repos:
        slug = _tool_slug(r)
        for c in tool_categories.get(slug, []):
            links.append({"source": slug, "target": c})

    # ── Tool ↔ Tool links (shared topics ⊇ 2+, or same language) ─
    tool_list = list(tool_nodes)
    linked_pairs: set[tuple[str, str]] = set()

    repo_by_slug = {}
    for r in repos:
        repo_by_slug[_tool_slug(r)] = r

    for i in range(len(tool_list)):
        for j in range(i + 1, len(tool_list)):
            a_slug = tool_list[i]["id"]
            b_slug = tool_list[j]["id"]
            a_repo = repo_by_slug.get(a_slug, {})
            b_repo = repo_by_slug.get(b_slug, {})

            a_topics = set(t.lower() for t in a_repo.get("topics", []))
            b_topics = set(t.lower() for t in b_repo.get("topics", []))

            shared = a_topics & b_topics

            # Connect if share 2+ meaningful topics, or same language + 1 topic
            meaningful_shared = {t for t in shared if t not in {"osint", "hacking", "python", "security", "cli", "linux"}}
            connection = False

            if len(meaningful_shared) >= 2:
                connection = True
            elif len(meaningful_shared) >= 1 and tool_list[i].get("language") and tool_list[i]["language"] == tool_list[j]["language"]:
                connection = True

            if connection:
                key = (a_slug, b_slug) if a_slug < b_slug else (b_slug, a_slug)
                if key not in linked_pairs:
                    linked_pairs.add(key)
                    links.append({"source": a_slug, "target": b_slug})

    return {"nodes": nodes, "links": links}


def _tool_slug(r: dict) -> str:
    """Create a unique slug for a repo."""
    return r.get("full_name", r.get("name", "")).replace("/", "-").lower()


def summarize_repo(repo: dict) -> dict:
    name = repo.get("full_name", repo.get("name", ""))
    description = (repo.get("description") or "").strip()
    language = repo.get("language") or ""
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    topics = ", ".join(repo.get("topics", []))
    html_url = repo.get("html_url", f"https://github.com/{name}")
    updated = (repo.get("updated_at") or "")[:10]
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


def write_csv(rows: list[dict], path: Path):
    fieldnames = ["Repo", "Description", "Language", "Stars", "Forks", "Topics", "Updated", "URL"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_graph_summary(graph: dict):
    """Print a text summary of the graph structure."""
    nodes = graph["nodes"]
    links = graph["links"]

    parent_nodes = [n for n in nodes if n["type"] == "parent"]
    cat_nodes = [n for n in nodes if n["type"] == "category"]
    tool_nodes = [n for n in nodes if n["type"] == "tool"]

    print(f"\n  ┌─ Graph Structure ──────────────────────────────")
    print(f"  │  {len(parent_nodes):>3} root node")
    print(f"  │  {len(cat_nodes):>3} categories")
    print(f"  │  {len(tool_nodes):>3} tools")
    print(f"  │  {len(links):>3} connections (edges)")
    print(f"  └────────────────────────────────────────────────")

    # Show category breakdown
    print(f"\n  ┌─ Category Distribution ─────────────────────────")
    for cat_node in cat_nodes:
        count = sum(1 for l in links if l["target"] == cat_node["id"])
        bar = "█" * max(1, count // 5)
        print(f"  │  {cat_node['label']:40s} {count:3d} tools  {bar}")
    print(f"  └────────────────────────────────────────────────")

    # Top tools by stars with category tags
    top_tools = sorted(tool_nodes, key=lambda n: n.get("stars", 0), reverse=True)[:10]
    print(f"\n  ┌─ Top 10 Tools (by stars) ───────────────────────")
    for n in top_tools:
        cats = [l["target"] for l in links if l["source"] == n["id"] and l["target"] in {c["id"] for c in cat_nodes}]
        cat_labels = [CATEGORIES.get(c, {}).get("label", c) for c in cats[:2]]
        tag = " | ".join(cat_labels) if cat_labels else ""
        stars = n.get("stars", 0)
        print(f"  │  ⭐{stars:>6}  {n['label']:45s}  [{tag}]")
    print(f"  └────────────────────────────────────────────────")


def main():
    today = date.today().isoformat()

    print("=" * 60)
    print("  Hermes_scan — OSINT Scanning Tools Report")
    print(f"  Date: {today}")
    print("=" * 60)
    print(f"\n[*] Running {len(SEARCH_QUERIES)} search queries...\n")

    repos = collect_osint_repos()
    print(f"\n[*] Total unique OSINT scanning tool repos: {len(repos)}")

    print(f"\n[*] Generating knowledge graph...")
    graph = build_graph(repos)

    print(f"\n[*] Generating summaries...")
    rows = [summarize_repo(r) for r in repos]

    # ── Write outputs ──────────────────────────────────────────
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    # CSV report
    csv_path = CSV_DIR / f"scan_report_{today}.csv"
    write_csv(rows, csv_path)
    print(f"\n[+] CSV report: {csv_path} ({len(rows)} repos)")

    # Graph JSON
    graph_path = CSV_DIR / f"graph_{today}.json"
    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    print(f"[+] Graph JSON:  {graph_path} ({len(graph['nodes'])} nodes, {len(graph['links'])} edges)")

    # Latest symlinks
    latest_csv = CSV_DIR / "latest.csv"
    write_csv(rows, latest_csv)
    print(f"[+] Latest CSV:  {latest_csv}")

    latest_graph = CSV_DIR / "latest-graph.json"
    with open(latest_graph, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    print(f"[+] Latest JSON: {latest_graph}")

    # Print graph summary
    print_graph_summary(graph)

    # ── Auto-commit and push ──────────────────────────────────
    os.chdir(REPO_DIR)
    subprocess.run(
        ["git", "add", str(csv_path), str(graph_path), str(latest_csv), str(latest_graph)],
        capture_output=True,
    )
    result = subprocess.run(
        ["git", "commit", "-m", f"chore: daily OSINT scan {today} [{len(rows)} tools, {len(graph['nodes'])} nodes]"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        subprocess.run(["git", "push"], capture_output=True)
        print(f"\n[+] Committed and pushed to remote.")
    else:
        print(f"\n[*] No new changes to commit.")


if __name__ == "__main__":
    main()

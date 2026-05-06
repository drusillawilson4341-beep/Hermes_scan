# Hermes_scan

Daily scan of **OSINT (Open Source Intelligence) scanning tools** on GitHub — discovers and catalogs open-source OSINT repositories, extracts descriptions, and generates both tabular reports and **knowledge graphs** showing tool connections.

## Overview

Every day at **10:00 AM (Asia/Shanghai)**, this project:
1. Searches GitHub for OSINT scanning tool repositories (topic-based + well-known tools)
2. Extracts descriptions, language, stars, forks, topics for each repo
3. **Categorizes tools** into 9 functional categories
4. Generates a **knowledge graph** (JSON) showing tool connections
5. Auto-commits and pushes to this repository

## Reports

### CSV Reports

Located in [`reports/`](./reports/), named `scan_report_YYYY-MM-DD.csv`.

| Field       | Description                              |
|-------------|------------------------------------------|
| Repo        | Full repository name (owner/repo)        |
| Description | Brief functional summary                 |
| Language    | Primary programming language             |
| Stars       | Star count                               |
| Forks       | Fork count                               |
| Topics      | Repository topic tags                    |
| Updated     | Last update date                         |
| URL         | Link to the repository                   |

### Knowledge Graph (JSON)

Located in [`reports/`](./reports/), named `graph_YYYY-MM-DD.json`.

This file mirrors the structure of the [knowledge-search system](https://github.com/drusillawilson4341-beep/knowledge-search) graph format, with three node types:

```
nodes: [{id, label, type, stars?, language?}]
links: [{source, target}]
```

| Node Type   | Description                                      |
|-------------|--------------------------------------------------|
| `parent`    | Root node: "OSINT Scanning Tools"                |
| `category`  | Tool category clusters (9 categories)            |
| `tool`      | Individual repository nodes                      |

**Connections (edges) include:**
- **Category membership** — root → category → tool
- **Tool ↔ Tool** — based on shared topics (2+ shared meaningful topics) or same programming language + shared topic

### Latest References

- `reports/latest.csv` — most recent CSV report
- `reports/latest-graph.json` — most recent knowledge graph

## Category Distribution

| Category | Example Tools |
|----------|--------------|
| **Domain & Network Reconnaissance** | Amass, subfinder, theHarvester, nuclei, bbot, OneForAll, reconftw |
| **Social Media OSINT** | Sherlock, maigret, GHunt, social-analyzer, instaloader, Osintgram |
| **Threat Intelligence & Monitoring** | SpiderFoot, worldmonitor, web-check |
| **Email & Phone OSINT** | holehe, phoneinfoga, toutatis |
| **OSINT Frameworks & Dashboards** | reNgine, Datasploit, Seeker, OSINT-Framework |
| **Dark Web & Tor OSINT** | OnionSearch, pryingdeep |
| **Web Analysis & Crawling** | Photon, SingleFile, WhatWeb |
| **Social Engineering & Tracking** | GhostTrack, Social Engineering Toolkit |
| **Code & Secret Scanning** | Secret scanning tools |

## Local Setup

```bash
git clone https://github.com/drusillawilson4341-beep/Hermes_scan.git
cd Hermes_scan
python3 scan_repos.py
```

Requires a `.env` file with:

```
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx
```

## Tech Stack

- Python 3 (stdlib only — no external dependencies)
- GitHub REST API v3 (search + repos endpoints)
- Git for automated commits
- Hermes cron scheduler (`0 10 * * *`)

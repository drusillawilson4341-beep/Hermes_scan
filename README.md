# Hermes_scan

Daily scan of **OSINT (Open Source Intelligence) scanning tools** on GitHub — discovers and catalogs open-source OSINT repositories, extracts descriptions, and generates CSV reports.

## Overview

Every day at **10:00 AM (Asia/Shanghai)**, this project:
1. Searches GitHub for OSINT scanning tool repositories (topic-based + well-known tools)
2. Extracts descriptions, language, stars, forks, topics for each repo
3. Generates a timestamped CSV report in `reports/`
4. Auto-commits and pushes to this repository

### Search Coverage

The script runs **25+ search queries** covering:
- Topic-based: `topic:osint`, `topic:osint-tools`, `topic:reconnaissance`, `topic:information-gathering`, `topic:recon`
- Name-based: sherlock, maigret, theHarvester, spiderfoot, GHunt, Amass, subfinder, holehe, and more

Results are **deduplicated** and sorted by star count.

## Reports

Reports are stored in [`reports/`](./reports/), named `scan_report_YYYY-MM-DD.csv`.
A `latest.csv` always points to the most recent scan.

### CSV Fields

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

## Example Results

| Repo | Stars | Description |
|------|-------|-------------|
| sherlock-project/sherlock | 82K | Hunt down social media accounts by username |
| Lissy93/web-check | 33K | All-in-one OSINT tool for analysing any website |
| smicallef/spiderfoot | 17K | OSINT automation for threat intelligence |
| laramies/theHarvester | 16K | E-mails, subdomains and names Harvester |
| owasp-amass/amass | 14K | In-depth attack surface mapping |
| projectdiscovery/subfinder | 13K | Fast passive subdomain enumeration |

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

# Hermes_scan

Daily scan of human-developed repositories — analyzes repo descriptions and READMEs, generates CSV reports.

## Overview

Every day at **10:00 AM (Asia/Shanghai)**, this project:
1. Fetches all repositories under [drusillawilson4341-beep](https://github.com/drusillawilson4341-beep)
2. Extracts descriptions and README summaries for each repo
3. Generates a timestamped CSV report in `reports/`
4. Auto-commits and pushes to this repository

## Reports

Reports are stored in [`reports/`](./reports/), named `scan_report_YYYY-MM-DD.csv`.
A `latest.csv` symlink always points to the most recent scan.

### CSV Fields

| Field         | Description                                    |
|---------------|------------------------------------------------|
| Repo          | Repository name                                |
| Description   | Brief functional summary (from README/desc)    |
| Language      | Primary programming language                   |
| Stars         | Star count                                     |
| Forks         | Fork count                                     |
| Topics        | Repository topics                              |
| URL           | Link to the repository                         |

## Local Setup

```bash
git clone https://github.com/drusillawilson4341-beep/Hermes_scan.git
cd Hermes_scan
python3 scan_repos.py
```

Requires a `.env` file with:

```
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx
GITHUB_OWNER=drusillawilson4341-beep
```

## Tech Stack

- Python 3 (stdlib only — no external dependencies)
- GitHub REST API v3
- Git for automated commits
- Hermes cron scheduler (`0 10 * * *`)

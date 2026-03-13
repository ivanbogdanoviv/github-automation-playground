# github-automation-playground

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Bash](https://img.shields.io/badge/Bash-4EAA25?style=flat&logo=gnubash&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat&logo=github-actions&logoColor=white)
![CI/CD](https://img.shields.io/badge/CI%2FCD-Pipeline-orange?style=flat)

A collection of real GitHub Actions workflows, automation scripts, and CI/CD patterns built to sharpen DevOps fundamentals — directly supporting the **GitHub Automation Playground** project on my [portfolio](https://ivanbiv.com).

This repo is both a learning lab and a reference: every workflow here solves a real problem, is documented with context, and is ready to fork and reuse.

---

## What's Inside

| Workflow | File | Purpose |
|----------|------|---------|
| Lint & Test | `.github/workflows/lint-and-test.yml` | Run linters and tests on every push/PR |
| Auto-Label Issues | `.github/workflows/auto-label-issues.yml` | Label new issues by keyword match |
| Weekly Digest | `.github/workflows/weekly-digest.yml` | Scheduled summary of repo activity |
| Matrix Build | `examples/matrix-build/` | Build across multiple OS/version combos |
| Scheduled Job | `examples/scheduled-job/` | Cron-triggered workflow template |

---

## Folder Structure

```
github-automation-playground/
├── .github/
│   └── workflows/
│       ├── lint-and-test.yml       # Triggered on push and pull_request
│       ├── auto-label-issues.yml   # Triggered on issues: opened
│       └── weekly-digest.yml       # Scheduled: every Monday 09:00 UTC
├── scripts/
│   ├── repo_stats.py               # Query GitHub API for repo activity stats
│   └── cleanup_branches.sh         # Delete stale merged branches via GitHub API
├── examples/
│   ├── matrix-build/               # Multi-OS, multi-version CI matrix example
│   └── scheduled-job/              # Cron workflow template with annotations
└── docs/
    └── workflow-reference.md       # Field-by-field YAML reference guide
```

---

## Quick Start

### Use a workflow in your own repo

1. Fork or copy the workflow file from `.github/workflows/`
2. Adjust the trigger events, environment variables, and steps for your project
3. Add any required secrets under **Settings → Secrets and variables → Actions**

### Run the scripts locally

```bash
# Install dependencies
pip install requests python-dotenv

# Get repo stats (set your token first)
export GITHUB_TOKEN=ghp_yourtoken
python scripts/repo_stats.py --owner yourname --repo yourrepo

# Clean up merged branches (dry-run by default)
bash scripts/cleanup_branches.sh --owner yourname --repo yourrepo
```

---

## Secrets Setup

| Secret Name | Used By | Notes |
|-------------|---------|-------|
| `GITHUB_TOKEN` | All workflows | Auto-provided by Actions runner |
| `LABEL_TOKEN` | auto-label-issues | Needs `issues: write` permission |

> Tip: For personal repos, the default `GITHUB_TOKEN` covers most use cases.

---

## Workflow Highlights

### `lint-and-test.yml`
Runs on every push and pull request. Uses a matrix to test against multiple Python versions. Fails fast on lint errors before running tests.

### `auto-label-issues.yml`
Reads the issue title and body, matches against a keyword map, and applies labels automatically — keeping the issue tracker organized with zero manual triage.

### `weekly-digest.yml`
Scheduled every Monday. Calls the GitHub API to summarize new issues, PRs, and commits from the past week, then posts results as a workflow summary.

---

## Tech Stack

- **GitHub Actions** — workflow orchestration
- **Python 3** + `requests` — GitHub API scripting
- **Bash** — branch and repo housekeeping
- **YAML** — workflow definitions

---

## Portfolio Connection

This repo supports the **GitHub Automation Playground** project on my [portfolio](https://ivanbiv.com), showcasing CI/CD pipeline design, event-driven automation, and GitHub API integration as practical DevOps skills.

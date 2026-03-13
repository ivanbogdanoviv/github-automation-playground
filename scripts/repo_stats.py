#!/usr/bin/env python3
# =============================================================================
# repo_stats.py — GitHub Repository Activity Stats
# =============================================================================
# Purpose:
#   Queries the GitHub REST API to produce an activity summary for any public
#   or private repository. Designed for use in weekly digest workflows,
#   CI/CD pipelines, and manual reporting from the command line.
#
# Usage:
#   python repo_stats.py --owner <owner> --repo <repo>
#   python repo_stats.py --owner <owner> --repo <repo> --digest
#   python repo_stats.py --owner <owner> --repo <repo> --since 2026-01-01
#   python repo_stats.py --owner <owner> --repo <repo> --json
#
# Required environment variables:
#   GITHUB_TOKEN  — Personal access token with at least repo:read scope.
#                   Without this, requests are unauthenticated (60 req/hr limit).
#                   Set in .env or export before running.
#
# Optional environment variables:
#   (none — all config is via CLI flags; see --help for full reference)
#
# Output modes:
#   Default     : Colored terminal table (overview + recent activity)
#   --digest    : Activity digest for the last 7 days (or --since window)
#   --json      : Machine-readable JSON for piping into other tools
#
# Dependencies:
#   pip install requests python-dotenv
# =============================================================================
"""
repo_stats.py — Query the GitHub API for repo activity stats.

Usage:
    python repo_stats.py --owner <owner> --repo <repo>
    python repo_stats.py --owner <owner> --repo <repo> --digest
    python repo_stats.py --owner <owner> --repo <repo> --since 2026-01-01
    python repo_stats.py --owner <owner> --repo <repo> --since 2026-01-01 --json

Options:
    --owner     GitHub username or org
    --repo      Repository name
    --digest    Print a weekly digest summary (issues, PRs, commits in last 7 days)
    --since     Filter activity since this date (YYYY-MM-DD). Overrides --digest window.
    --json      Output stats as JSON instead of formatted terminal output

Requirements:
    pip install requests python-dotenv

Set GITHUB_TOKEN in your environment or a .env file.
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.github.com"

# ── ANSI colors ───────────────────────────────────────────────
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def c(text, code):
    """Wrap text in an ANSI color code (skipped when stdout is not a TTY)."""
    if not sys.stdout.isatty():
        return str(text)
    return f"{code}{text}{RESET}"


def get_headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch(url: str, params: dict = None) -> list | dict:
    resp = requests.get(url, headers=get_headers(), params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_paginated(url: str, params: dict = None) -> list:
    """Fetch all pages from a paginated GitHub endpoint."""
    params = params or {}
    params.setdefault("per_page", 100)
    results = []
    page = 1
    while True:
        params["page"] = page
        data = fetch(url, params=dict(params))
        if not data:
            break
        if isinstance(data, list):
            results.extend(data)
            if len(data) < params["per_page"]:
                break
        else:
            return data
        page += 1
    return results


def parse_since(since_str: str) -> str:
    """Parse a YYYY-MM-DD string and return ISO 8601 UTC timestamp."""
    dt = datetime.strptime(since_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return dt.isoformat()


def get_repo_info(owner: str, repo: str) -> dict:
    return fetch(f"{BASE_URL}/repos/{owner}/{repo}")


def get_open_issues(owner: str, repo: str, since: str) -> list:
    """Returns issues (excluding PRs) opened since the given ISO timestamp."""
    items = fetch_paginated(
        f"{BASE_URL}/repos/{owner}/{repo}/issues",
        params={"state": "open", "since": since, "per_page": 100},
    )
    return [i for i in items if "pull_request" not in i]


def get_open_prs(owner: str, repo: str, since: str) -> list:
    items = fetch_paginated(
        f"{BASE_URL}/repos/{owner}/{repo}/pulls",
        params={"state": "open", "sort": "created", "direction": "desc"},
    )
    return [p for p in items if p["created_at"] >= since]


def get_recent_commits(owner: str, repo: str, since: str) -> list:
    return fetch_paginated(
        f"{BASE_URL}/repos/{owner}/{repo}/commits",
        params={"since": since, "per_page": 100},
    )


def get_top_contributors(commits: list, top_n: int = 5) -> list[tuple]:
    """Return top N contributors by commit count from a commits list."""
    counter = Counter()
    for commit in commits:
        author = (
            commit.get("author") or {}
        ).get("login") or commit["commit"]["author"]["name"]
        counter[author] += 1
    return counter.most_common(top_n)


def get_most_active_files(owner: str, repo: str, commits: list, top_n: int = 5) -> list[tuple]:
    """
    Return top N most-changed files across the given commits.
    Fetches commit detail for up to 30 recent commits (API rate limit friendly).
    """
    file_counter = Counter()
    for commit in commits[:30]:
        sha = commit["sha"]
        try:
            detail = fetch(f"{BASE_URL}/repos/{owner}/{repo}/commits/{sha}")
            for f in detail.get("files", []):
                file_counter[f["filename"]] += 1
        except Exception:
            continue
    return file_counter.most_common(top_n)


def collect_stats(owner: str, repo: str, since: str, include_files: bool = False) -> dict:
    """Collect all stats and return as a dict."""
    info        = get_repo_info(owner, repo)
    issues      = get_open_issues(owner, repo, since)
    prs         = get_open_prs(owner, repo, since)
    commits     = get_recent_commits(owner, repo, since)
    contributors = get_top_contributors(commits)
    active_files = get_most_active_files(owner, repo, commits) if include_files else []

    return {
        "repo":         f"{owner}/{repo}",
        "since":        since[:10],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overview": {
            "stars":       info["stargazers_count"],
            "forks":       info["forks_count"],
            "open_issues": info["open_issues_count"],
            "language":    info["language"],
            "updated_at":  info["updated_at"],
        },
        "activity": {
            "open_issues_since_date":  len(issues),
            "open_prs_since_date":     len(prs),
            "commits_since_date":      len(commits),
        },
        "recent_commits": [
            {
                "sha":     cm["sha"][:7],
                "author":  (cm.get("author") or {}).get("login")
                           or cm["commit"]["author"]["name"],
                "message": cm["commit"]["message"].splitlines()[0][:72],
                "date":    cm["commit"]["author"]["date"][:10],
            }
            for cm in commits[:10]
        ],
        "top_contributors": [
            {"login": login, "commits": count} for login, count in contributors
        ],
        "most_active_files": [
            {"file": f, "changes": n} for f, n in active_files
        ],
    }


def print_stats(stats: dict) -> None:
    """Print stats with color-coded terminal output."""
    ov = stats["overview"]
    ac = stats["activity"]

    print(c(f"\n{'='*60}", CYAN))
    print(c(f"  Repo Stats: {stats['repo']}", BOLD))
    print(c(f"  Since: {stats['since']}  |  Generated: {stats['generated_at'][:19]}Z", DIM))
    print(c(f"{'='*60}", CYAN))

    print(c("\nOVERVIEW", YELLOW))
    print(f"  {'Stars':<22} {c(ov['stars'], GREEN)}")
    print(f"  {'Forks':<22} {c(ov['forks'], GREEN)}")
    print(f"  {'Open Issues (total)':<22} {c(ov['open_issues'], GREEN)}")
    print(f"  {'Language':<22} {c(ov['language'] or 'N/A', GREEN)}")
    print(f"  {'Last Updated':<22} {c(ov['updated_at'][:10], GREEN)}")

    print(c(f"\nACTIVITY SINCE {stats['since']}", YELLOW))
    print(f"  {'Open Issues':<22} {c(ac['open_issues_since_date'], GREEN)}")
    print(f"  {'Open PRs':<22} {c(ac['open_prs_since_date'], GREEN)}")
    print(f"  {'Commits':<22} {c(ac['commits_since_date'], GREEN)}")

    if stats["recent_commits"]:
        print(c("\nRECENT COMMITS", YELLOW))
        for cm in stats["recent_commits"][:5]:
            print(f"  {c(cm['sha'], DIM)} {c(cm['date'], DIM)}  "
                  f"{c('[' + cm['author'] + ']', CYAN)}  {cm['message']}")

    if stats["top_contributors"]:
        print(c("\nTOP CONTRIBUTORS", YELLOW))
        for entry in stats["top_contributors"]:
            bar = "█" * min(entry["commits"], 20)
            print(f"  {entry['login']:<20} {c(bar, GREEN)} {entry['commits']}")

    if stats["most_active_files"]:
        print(c("\nMOST ACTIVE FILES", YELLOW))
        for entry in stats["most_active_files"]:
            print(f"  {c(entry['changes'], YELLOW)}x  {entry['file']}")

    print(c(f"\n{'='*60}\n", CYAN))


def weekly_digest(owner: str, repo: str, since: str = None, as_json: bool = False) -> None:
    if since is None:
        since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    stats = collect_stats(owner, repo, since)

    if as_json:
        print(json.dumps(stats, indent=2))
        return

    print_stats(stats)


def main():
    parser = argparse.ArgumentParser(description="GitHub repo activity stats.")
    parser.add_argument("--owner",  required=True, help="GitHub username or org")
    parser.add_argument("--repo",   required=True, help="Repository name")
    parser.add_argument("--digest", action="store_true",
                        help="Print activity digest for the last 7 days")
    parser.add_argument("--since",  metavar="YYYY-MM-DD",
                        help="Filter activity since this date (overrides --digest window)")
    parser.add_argument("--json",   action="store_true",
                        help="Output stats as JSON")
    args = parser.parse_args()

    # Resolve `since` timestamp
    if args.since:
        try:
            since_ts = parse_since(args.since)
        except ValueError:
            print(f"Error: --since must be in YYYY-MM-DD format, got: {args.since}", file=sys.stderr)
            sys.exit(1)
    elif args.digest:
        since_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    else:
        since_ts = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    if args.digest or args.since:
        weekly_digest(args.owner, args.repo, since=since_ts, as_json=args.json)
    else:
        # Default: show repo overview
        info = get_repo_info(args.owner, args.repo)
        if args.json:
            print(json.dumps({
                "repo":        info["full_name"],
                "stars":       info["stargazers_count"],
                "forks":       info["forks_count"],
                "open_issues": info["open_issues_count"],
                "language":    info["language"],
                "updated_at":  info["updated_at"],
            }, indent=2))
        else:
            print(c(f"\n{'='*45}", CYAN))
            print(c(f"  {info['full_name']}", BOLD))
            print(c(f"{'='*45}", CYAN))
            print(f"  {'Stars':<18} {c(info['stargazers_count'], GREEN)}")
            print(f"  {'Forks':<18} {c(info['forks_count'], GREEN)}")
            print(f"  {'Open Issues':<18} {c(info['open_issues_count'], GREEN)}")
            print(f"  {'Language':<18} {c(info['language'] or 'N/A', GREEN)}")
            print(f"  {'Updated':<18} {c(info['updated_at'][:10], GREEN)}")
            print(c(f"{'='*45}\n", CYAN))


if __name__ == "__main__":
    main()

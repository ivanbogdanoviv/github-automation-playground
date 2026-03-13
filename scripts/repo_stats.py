#!/usr/bin/env python3
"""
repo_stats.py — Query the GitHub API for repo activity stats.

Usage:
    python repo_stats.py --owner <owner> --repo <repo> [--digest]

Options:
    --owner     GitHub username or org
    --repo      Repository name
    --digest    Print a weekly digest summary (issues, PRs, commits in last 7 days)

Requirements:
    pip install requests python-dotenv

Set GITHUB_TOKEN in your environment or a .env file.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.github.com"


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


def weekly_digest(owner: str, repo: str) -> None:
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    print(f"\n=== Weekly Digest: {owner}/{repo} ===")
    print(f"Period: last 7 days (since {since[:10]})\n")

    # Issues opened
    issues = fetch(f"{BASE_URL}/repos/{owner}/{repo}/issues",
                   params={"state": "open", "since": since, "per_page": 100})
    real_issues = [i for i in issues if "pull_request" not in i]
    print(f"  New issues opened : {len(real_issues)}")

    # Pull requests
    prs = fetch(f"{BASE_URL}/repos/{owner}/{repo}/pulls",
                params={"state": "all", "sort": "created", "direction": "desc", "per_page": 50})
    recent_prs = [p for p in prs if p["created_at"] >= since]
    print(f"  Pull requests     : {len(recent_prs)}")

    # Commits on default branch
    commits = fetch(f"{BASE_URL}/repos/{owner}/{repo}/commits",
                    params={"since": since, "per_page": 100})
    print(f"  Commits           : {len(commits)}")

    if commits:
        print("\n  Recent commits:")
        for c in commits[:5]:
            msg = c["commit"]["message"].splitlines()[0][:72]
            author = c["commit"]["author"]["name"]
            print(f"    - [{author}] {msg}")

    print("\n==========================================\n")


def main():
    parser = argparse.ArgumentParser(description="GitHub repo activity stats.")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--digest", action="store_true", help="Print weekly digest")
    args = parser.parse_args()

    if args.digest:
        weekly_digest(args.owner, args.repo)
    else:
        info = fetch(f"{BASE_URL}/repos/{args.owner}/{args.repo}")
        print(f"Repo       : {info['full_name']}")
        print(f"Stars      : {info['stargazers_count']}")
        print(f"Forks      : {info['forks_count']}")
        print(f"Open issues: {info['open_issues_count']}")
        print(f"Language   : {info['language']}")
        print(f"Updated    : {info['updated_at']}")


if __name__ == "__main__":
    main()

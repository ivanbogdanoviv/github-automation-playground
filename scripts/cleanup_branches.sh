#!/usr/bin/env bash
# cleanup_branches.sh — Delete stale merged branches via the GitHub API.
#
# Usage:
#   chmod +x cleanup_branches.sh
#   ./cleanup_branches.sh --owner <owner> --repo <repo> [--dry-run]
#
# Requirements:
#   - GITHUB_TOKEN env var with repo scope
#   - curl, jq
#
# By default runs in dry-run mode. Pass --no-dry-run to actually delete.

set -euo pipefail

OWNER=""
REPO=""
DRY_RUN=true
BASE_BRANCH="main"

usage() {
  echo "Usage: $0 --owner <owner> --repo <repo> [--no-dry-run]"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner)      OWNER="$2";    shift 2 ;;
    --repo)       REPO="$2";     shift 2 ;;
    --no-dry-run) DRY_RUN=false; shift   ;;
    *)            usage ;;
  esac
done

[[ -z "$OWNER" || -z "$REPO" ]] && usage

TOKEN="${GITHUB_TOKEN:-}"
if [[ -z "$TOKEN" ]]; then
  echo "[ERROR] GITHUB_TOKEN is not set."
  exit 1
fi

API="https://api.github.com/repos/${OWNER}/${REPO}"
AUTH_HEADER="Authorization: Bearer ${TOKEN}"

echo "=== Branch Cleanup: ${OWNER}/${REPO} ==="
echo "Mode: $( $DRY_RUN && echo 'DRY RUN (no deletions)' || echo 'LIVE — will delete!' )"
echo ""

# Fetch merged PRs to get a list of merged branch names
merged_branches=$(curl -s -H "$AUTH_HEADER" \
  "${API}/pulls?state=closed&per_page=100" | \
  jq -r '.[] | select(.merged_at != null) | .head.ref')

deleted=0
skipped=0

for branch in $merged_branches; do
  # Never delete protected branches
  if [[ "$branch" == "main" || "$branch" == "master" || "$branch" == "dev" ]]; then
    echo "  [SKIP] $branch (protected)"
    ((skipped++))
    continue
  fi

  if $DRY_RUN; then
    echo "  [DRY-RUN] Would delete: $branch"
  else
    status=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
      -H "$AUTH_HEADER" "${API}/git/refs/heads/${branch}")
    if [[ "$status" == "204" ]]; then
      echo "  [DELETED] $branch"
      ((deleted++))
    else
      echo "  [ERROR]   $branch — HTTP $status"
    fi
  fi
done

echo ""
echo "Done. Deleted: $deleted | Skipped: $skipped"

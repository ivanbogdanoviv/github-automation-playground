"""
tests/test_repo_stats.py — Pytest tests for repo_stats.py

Tests cover:
- Stats calculation functions
- --since date filter parsing
- JSON output format
- Top contributors logic
- API response mocking
- get_headers with/without token

Run with:
    pytest tests/test_repo_stats.py -v
"""

import importlib.util
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# ── Load module under test ────────────────────────────────────
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")


def load_repo_stats():
    path = os.path.join(SCRIPTS_DIR, "repo_stats.py")
    spec = importlib.util.spec_from_file_location("repo_stats", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture()
def rs():
    """Fresh import of repo_stats module for each test."""
    return load_repo_stats()


FAKE_REPO_INFO = {
    "full_name":        "testowner/testrepo",
    "stargazers_count": 42,
    "forks_count":      7,
    "open_issues_count": 3,
    "language":         "Python",
    "updated_at":       "2026-02-15T10:00:00Z",
}

FAKE_COMMITS = [
    {
        "sha": "abc1234",
        "author": {"login": "alice"},
        "commit": {
            "author": {"name": "Alice", "date": "2026-02-10T09:00:00Z"},
            "message": "feat: add cool feature",
        },
    },
    {
        "sha": "def5678",
        "author": {"login": "bob"},
        "commit": {
            "author": {"name": "Bob", "date": "2026-02-12T11:00:00Z"},
            "message": "fix: resolve null pointer",
        },
    },
    {
        "sha": "ghi9012",
        "author": {"login": "alice"},
        "commit": {
            "author": {"name": "Alice", "date": "2026-02-14T08:00:00Z"},
            "message": "docs: update README",
        },
    },
]

FAKE_ISSUES = [
    {"id": 1, "title": "Bug in login", "created_at": "2026-02-11T10:00:00Z"},
    {"id": 2, "title": "Feature request: dark mode", "created_at": "2026-02-13T14:00:00Z"},
]

FAKE_PRS = [
    {
        "id": 101,
        "title": "Add login feature",
        "created_at": "2026-02-12T09:00:00Z",
    },
]


# ── Test 1: Module imports cleanly ────────────────────────────

class TestModuleImport:
    def test_module_loads(self, rs):
        """repo_stats.py should import without errors."""
        assert rs is not None
        assert hasattr(rs, "get_headers")
        assert hasattr(rs, "collect_stats")
        assert hasattr(rs, "parse_since")
        assert hasattr(rs, "get_top_contributors")


# ── Test 2: get_headers ───────────────────────────────────────

class TestGetHeaders:
    def test_no_token(self, monkeypatch, rs):
        """Returns Accept header but no Authorization when token is absent."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        # Reload after env change
        mod = load_repo_stats()
        headers = mod.get_headers()
        assert "Accept" in headers
        assert "Authorization" not in headers

    def test_with_token(self, monkeypatch, rs):
        """Returns Bearer Authorization header when GITHUB_TOKEN is set."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_testtoken999")
        mod = load_repo_stats()
        headers = mod.get_headers()
        assert headers.get("Authorization") == "Bearer ghp_testtoken999"

    def test_accept_header_value(self, rs):
        """Accept header should use GitHub's v3 JSON media type."""
        headers = rs.get_headers()
        assert headers["Accept"] == "application/vnd.github+json"


# ── Test 3: parse_since ───────────────────────────────────────

class TestParseSince:
    def test_valid_date(self, rs):
        """parse_since returns an ISO 8601 UTC string."""
        result = rs.parse_since("2026-01-15")
        assert result.startswith("2026-01-15T")
        assert "+00:00" in result or "Z" in result or "UTC" in result

    def test_invalid_date_raises(self, rs):
        """parse_since raises ValueError for invalid date strings."""
        with pytest.raises(ValueError):
            rs.parse_since("not-a-date")

    def test_invalid_format_raises(self, rs):
        """parse_since raises ValueError for wrong format (DD-MM-YYYY)."""
        with pytest.raises(ValueError):
            rs.parse_since("15-01-2026")

    def test_returns_string(self, rs):
        """parse_since always returns a string."""
        assert isinstance(rs.parse_since("2026-03-01"), str)


# ── Test 4: get_top_contributors ─────────────────────────────

class TestGetTopContributors:
    def test_counts_correctly(self, rs):
        """Alice has 2 commits, Bob has 1 — should be ranked correctly."""
        result = rs.get_top_contributors(FAKE_COMMITS, top_n=5)
        assert result[0][0] == "alice"
        assert result[0][1] == 2
        assert result[1][0] == "bob"
        assert result[1][1] == 1

    def test_top_n_limit(self, rs):
        """top_n parameter limits results."""
        result = rs.get_top_contributors(FAKE_COMMITS, top_n=1)
        assert len(result) == 1

    def test_empty_commits(self, rs):
        """Empty commit list returns empty contributor list."""
        result = rs.get_top_contributors([])
        assert result == []

    def test_falls_back_to_name_when_no_login(self, rs):
        """Falls back to commit author name when GitHub login is absent."""
        commits = [
            {
                "sha": "xyz0001",
                "author": None,  # no GitHub account linked
                "commit": {
                    "author": {"name": "Anonymous Dev", "date": "2026-01-01T00:00:00Z"},
                    "message": "initial commit",
                },
            }
        ]
        result = rs.get_top_contributors(commits, top_n=5)
        assert result[0][0] == "Anonymous Dev"


# ── Test 5: collect_stats with mocked API ────────────────────

class TestCollectStats:
    @patch("requests.get")
    def test_collect_stats_returns_expected_keys(self, mock_get, rs):
        """collect_stats returns a dict with all required top-level keys."""
        def side_effect(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            if "/commits" in url and "sha" not in url.split("?")[0].split("/")[-1]:
                resp.json.return_value = FAKE_COMMITS
            elif "/issues" in url:
                resp.json.return_value = FAKE_ISSUES
            elif "/pulls" in url:
                resp.json.return_value = FAKE_PRS
            else:
                resp.json.return_value = FAKE_REPO_INFO
            return resp

        mock_get.side_effect = side_effect
        since = "2026-02-01T00:00:00+00:00"
        stats = rs.collect_stats("testowner", "testrepo", since, include_files=False)

        assert "repo" in stats
        assert "overview" in stats
        assert "activity" in stats
        assert "recent_commits" in stats
        assert "top_contributors" in stats
        assert stats["repo"] == "testowner/testrepo"

    @patch("requests.get")
    def test_collect_stats_overview_values(self, mock_get, rs):
        """collect_stats overview section maps correctly from API response."""
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = FAKE_REPO_INFO
        mock_get.return_value = resp

        # Patch paginated calls too
        with patch.object(rs, "get_open_issues", return_value=FAKE_ISSUES), \
             patch.object(rs, "get_open_prs",    return_value=FAKE_PRS), \
             patch.object(rs, "get_recent_commits", return_value=FAKE_COMMITS):

            since = "2026-02-01T00:00:00+00:00"
            stats = rs.collect_stats("testowner", "testrepo", since)

        assert stats["overview"]["stars"]  == 42
        assert stats["overview"]["forks"]  == 7
        assert stats["overview"]["language"] == "Python"


# ── Test 6: JSON output format ────────────────────────────────

class TestJsonOutput:
    @patch("requests.get")
    def test_json_output_is_valid(self, mock_get, rs, capsys):
        """When --json is used, output must be valid JSON."""
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = FAKE_REPO_INFO
        mock_get.return_value = resp

        with patch.object(rs, "get_open_issues",    return_value=FAKE_ISSUES), \
             patch.object(rs, "get_open_prs",        return_value=FAKE_PRS), \
             patch.object(rs, "get_recent_commits",  return_value=FAKE_COMMITS):

            since = "2026-02-01T00:00:00+00:00"
            stats = rs.collect_stats("testowner", "testrepo", since)
            print(json.dumps(stats, indent=2))

        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert isinstance(parsed, dict)
        assert "repo" in parsed
        assert "overview" in parsed

    @patch("requests.get")
    def test_json_contains_since_field(self, mock_get, rs):
        """JSON output includes the 'since' date used for filtering."""
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = FAKE_REPO_INFO
        mock_get.return_value = resp

        with patch.object(rs, "get_open_issues",   return_value=[]), \
             patch.object(rs, "get_open_prs",       return_value=[]), \
             patch.object(rs, "get_recent_commits", return_value=[]):

            since = rs.parse_since("2026-01-01")
            stats = rs.collect_stats("testowner", "testrepo", since)

        assert stats["since"] == "2026-01-01"

    @patch("requests.get")
    def test_json_activity_counts_match(self, mock_get, rs):
        """Activity counts in JSON match the length of mocked API responses."""
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = FAKE_REPO_INFO
        mock_get.return_value = resp

        with patch.object(rs, "get_open_issues",   return_value=FAKE_ISSUES), \
             patch.object(rs, "get_open_prs",       return_value=FAKE_PRS), \
             patch.object(rs, "get_recent_commits", return_value=FAKE_COMMITS):

            since = rs.parse_since("2026-02-01")
            stats = rs.collect_stats("testowner", "testrepo", since)

        assert stats["activity"]["open_issues_since_date"] == len(FAKE_ISSUES)
        assert stats["activity"]["open_prs_since_date"]    == len(FAKE_PRS)
        assert stats["activity"]["commits_since_date"]     == len(FAKE_COMMITS)


# ── Test 7: --since date filter integration ───────────────────

class TestSinceDateFilter:
    def test_parse_since_filters_by_year(self, rs):
        """Dates from 2026 are parsed into 2026 ISO timestamps."""
        ts = rs.parse_since("2026-01-01")
        assert ts.startswith("2026-01-01")

    def test_since_earlier_than_today(self, rs):
        """parse_since on a past date does not raise."""
        ts = rs.parse_since("2020-06-15")
        assert "2020-06-15" in ts

    @patch("requests.get")
    def test_since_used_in_commits_query(self, mock_get, rs):
        """The since parameter is forwarded to the commits API call."""
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = []
        mock_get.return_value = resp

        since = rs.parse_since("2026-03-01")
        rs.get_recent_commits("owner", "repo", since)

        # Verify any call included the since parameter
        called_params = mock_get.call_args_list
        assert any(
            "since" in (call.kwargs.get("params") or {})
            for call in called_params
        )

"""
Basic sanity tests for github-automation-playground scripts.
Run with: pytest --tb=short -q
"""

import importlib.util
import os
import sys

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")


def load_script(name: str):
    """Import a script from the scripts/ folder without executing __main__."""
    path = os.path.join(SCRIPTS_DIR, name)
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# repo_stats.py
# ---------------------------------------------------------------------------

class TestRepoStats:
    def test_module_imports(self):
        """repo_stats.py should import without errors."""
        mod = load_script("repo_stats.py")
        assert mod is not None

    def test_get_headers_no_token(self, monkeypatch):
        """get_headers() should return Accept header even without a token."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        mod = load_script("repo_stats.py")
        headers = mod.get_headers()
        assert "Accept" in headers
        assert "Authorization" not in headers

    def test_get_headers_with_token(self, monkeypatch):
        """get_headers() should include Bearer token when GITHUB_TOKEN is set."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        mod = load_script("repo_stats.py")
        headers = mod.get_headers()
        assert headers.get("Authorization") == "Bearer ghp_test123"


# ---------------------------------------------------------------------------
# Workflow YAML sanity checks
# ---------------------------------------------------------------------------

import glob
import yaml  # pip install pyyaml (added to requirements.txt)


WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows")


def workflow_files():
    return glob.glob(os.path.join(WORKFLOWS_DIR, "*.yml"))


class TestWorkflowYaml:
    def test_workflow_files_exist(self):
        """There should be at least one workflow file."""
        assert len(workflow_files()) >= 1

    def test_all_workflows_parse(self):
        """Every workflow YAML file should parse without errors."""
        for path in workflow_files():
            with open(path) as f:
                doc = yaml.safe_load(f)
            assert isinstance(doc, dict), f"{path} did not parse to a dict"

    def test_all_workflows_have_on_and_jobs(self):
        """Every workflow must have 'on' and 'jobs' keys."""
        for path in workflow_files():
            with open(path) as f:
                doc = yaml.safe_load(f)
            assert "on" in doc or True in doc, f"{path} missing 'on' trigger"
            assert "jobs" in doc, f"{path} missing 'jobs'"

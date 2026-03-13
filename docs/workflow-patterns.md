# GitHub Actions Workflow Patterns

A practical reference for common GitHub Actions patterns, with annotated YAML examples, pitfalls, and debugging techniques.

---

## Pattern 1 — Matrix Builds

Run the same job across multiple OS versions, Python versions, or any combination of variables. Useful for ensuring code works everywhere before merging.

```yaml
name: Matrix Build

on: [push, pull_request]

jobs:
  test:
    name: Test (Python ${{ matrix.python-version }} on ${{ matrix.os }})
    runs-on: ${{ matrix.os }}

    strategy:
      # Don't cancel all jobs when one fails — see all failures at once
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.10", "3.11", "3.12"]
        # Exclude combinations that don't make sense
        exclude:
          - os: windows-latest
            python-version: "3.10"

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip           # Cache pip dependencies between runs

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest --tb=short -q
```

**Key points:**
- `fail-fast: false` lets all matrix legs run even if one fails — you see the full picture.
- `matrix.include` adds extra variables to specific combinations without duplicating jobs.
- `matrix.exclude` removes specific combinations you don't need.
- Access matrix values anywhere with `${{ matrix.<variable> }}`.

---

## Pattern 2 — Conditional Steps

Run specific steps only under certain conditions: on a specific branch, when a file changes, or when a previous step succeeded/failed.

```yaml
name: Conditional Steps

on:
  push:
    branches: [main, develop]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Run tests
        id: tests
        run: pytest --tb=short -q

      # Only deploy on push to main (not on develop)
      - name: Deploy to production
        if: github.ref == 'refs/heads/main' && success()
        run: ./deploy.sh production

      # Only runs if tests failed — send an alert
      - name: Notify on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: "Tests failed on this PR. Please investigate."
            });

      # Always runs — upload logs whether tests pass or fail
      - name: Upload test logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-logs
          path: logs/

      # Only runs when a specific file changed
      - name: Regenerate docs
        if: contains(github.event.commits[0].modified, 'docs/')
        run: make docs
```

**Condition expressions:**
| Expression | When it runs |
|---|---|
| `success()` | Previous steps all succeeded (default) |
| `failure()` | Any previous step failed |
| `always()` | Regardless of outcome |
| `cancelled()` | Workflow was cancelled |
| `github.ref == 'refs/heads/main'` | Only on main branch |
| `github.event_name == 'pull_request'` | Only on PR events |

---

## Pattern 3 — Artifact Upload and Download

Pass files between jobs (which run in separate VMs) or persist build outputs for later inspection.

```yaml
name: Build and Test with Artifacts

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build project
        run: |
          mkdir -p dist
          python setup.py sdist bdist_wheel

      # Upload the built artifact — available to later jobs and for 30 days
      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist-packages-${{ github.run_id }}
          path: dist/
          retention-days: 30
          if-no-files-found: error   # Fail if nothing was built

  test:
    runs-on: ubuntu-latest
    needs: build    # Wait for build job to finish before running

    steps:
      - uses: actions/checkout@v4

      # Download what the build job produced
      - name: Download build artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist-packages-${{ github.run_id }}
          path: dist/

      - name: Install and test
        run: |
          pip install dist/*.whl
          pytest

  publish:
    runs-on: ubuntu-latest
    needs: test
    if: github.ref == 'refs/heads/main'

    steps:
      - name: Download artifacts for publish
        uses: actions/download-artifact@v4
        with:
          name: dist-packages-${{ github.run_id }}
          path: dist/

      - name: Publish to PyPI
        env:
          TWINE_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

**Key points:**
- `needs:` creates a dependency chain between jobs.
- Artifacts are scoped to a workflow run — use `github.run_id` in the name to avoid collisions.
- Max artifact size is 500 MB per upload (GitHub-hosted runners).
- Use `actions/cache@v4` instead of artifacts for caching dependencies between runs.

---

## Pattern 4 — Environment Secrets and Variables

Scope secrets and variables to specific environments (staging, production) with optional protection rules.

```yaml
name: Deploy with Environment Secrets

on:
  push:
    branches: [main]

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    # Named environment — can require manual approval before running
    environment: staging

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to staging
        env:
          # Secrets scoped to the 'staging' environment
          DB_URL:    ${{ secrets.STAGING_DB_URL }}
          API_KEY:   ${{ secrets.STAGING_API_KEY }}
          # Non-secret environment variable (visible in logs)
          APP_ENV:   ${{ vars.APP_ENV }}
        run: ./scripts/deploy.sh staging

  deploy-production:
    runs-on: ubuntu-latest
    needs: deploy-staging
    # Production environment — configure required reviewers in repo Settings
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to production
        env:
          DB_URL:  ${{ secrets.PROD_DB_URL }}
          API_KEY: ${{ secrets.PROD_API_KEY }}
        run: ./scripts/deploy.sh production
```

**Where to set secrets:**
- **Repo secrets:** Settings → Secrets and variables → Actions → New repository secret
- **Environment secrets:** Settings → Environments → `<env name>` → Add secret
- **Org secrets:** Available to all repos in the org (org admins only)

**Rules:**
- Secrets are masked in logs — they appear as `***`.
- Never print secrets with `echo` — even masked values can leak via timing attacks.
- Use `vars.*` (not `secrets.*`) for non-sensitive config that's OK to show in logs.
- Environment protection rules (required reviewers, wait timer) block the job until approved.

---

## Pattern 5 — Reusable Workflows

Define a workflow once and call it from multiple other workflows. Eliminates copy-paste and keeps CI logic DRY.

```yaml
# .github/workflows/reusable-test.yml
# This is the reusable workflow — it is NOT triggered directly

name: Reusable Test Suite

on:
  workflow_call:
    inputs:
      python-version:
        description: Python version to test with
        required: false
        default: "3.12"
        type: string
      run-integration:
        description: Whether to run integration tests
        required: false
        default: false
        type: boolean
    secrets:
      TEST_API_KEY:
        description: API key for integration tests
        required: false

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python-version }}
          cache: pip

      - run: pip install -r requirements.txt

      - name: Run unit tests
        run: pytest tests/unit/ -v

      - name: Run integration tests
        if: inputs.run-integration == true
        env:
          API_KEY: ${{ secrets.TEST_API_KEY }}
        run: pytest tests/integration/ -v
```

```yaml
# .github/workflows/ci.yml — Caller workflow

name: CI

on: [push, pull_request]

jobs:
  unit-tests:
    uses: ./.github/workflows/reusable-test.yml
    with:
      python-version: "3.12"
      run-integration: false

  integration-tests:
    uses: ./.github/workflows/reusable-test.yml
    with:
      python-version: "3.12"
      run-integration: true
    secrets:
      TEST_API_KEY: ${{ secrets.TEST_API_KEY }}
```

**Key points:**
- Reusable workflows use `workflow_call` as the trigger.
- `inputs` pass configuration; `secrets` pass sensitive values.
- Call with `uses: owner/repo/.github/workflows/file.yml@ref` for cross-repo reuse.
- Reusable workflows count as a single job toward the 20-job concurrency limit.

---

## Common Pitfalls

| Pitfall | What Happens | Fix |
|---|---|---|
| Forgetting `needs:` between dependent jobs | Jobs run in parallel even though they depend on each other's output | Add `needs: [job-name]` to the downstream job |
| Using `set-env` or `add-path` directly | Security risk — deprecated commands | Use `$GITHUB_ENV` and `$GITHUB_PATH` files instead |
| Hardcoding branch names (`main`) | Breaks on repos using `master` or feature branches | Use `github.event.repository.default_branch` |
| Not pinning action versions | `@main` or `@latest` can break when the action updates | Pin to a commit SHA: `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683` |
| Running expensive jobs on every push | Wastes minutes and money | Use `paths:` filter to only trigger when relevant files change |
| Exposing secrets in `run:` commands | Secrets can appear in logs via argument lists | Pass secrets via `env:` variables, not command arguments |
| Not setting `permissions:` | Default permissions may be too broad or too narrow | Always declare the minimum needed: `permissions: contents: read` |

---

## Debugging Techniques

### 1 — Enable Step Debug Logging

Set this repository secret to get verbose output from every step:
```
ACTIONS_STEP_DEBUG = true
```

Or set it per-run by re-running with the "Enable debug logging" checkbox in the GitHub UI.

### 2 — Add a Debug Step

Print context and environment variables to understand what the runner sees:

```yaml
- name: Debug context
  run: |
    echo "github.ref       = ${{ github.ref }}"
    echo "github.event_name= ${{ github.event_name }}"
    echo "runner.os        = ${{ runner.os }}"
    env | sort
```

### 3 — Interactive Debugging with tmate

Drop an interactive SSH session into a running workflow for live debugging. **Never use on public repos with secrets.**

```yaml
- name: Debug with tmate (on failure only)
  if: failure()
  uses: mxschmitt/action-tmate@v3
  with:
    limit-access-to-actor: true   # Only the repo owner can connect
  timeout-minutes: 15
```

The step prints an SSH command in the logs. Connect, debug, then `touch /continue` to let the workflow proceed.

### 4 — Dump the Full Event Payload

```yaml
- name: Dump event payload
  run: cat $GITHUB_EVENT_PATH | python3 -m json.tool
```

### 5 — Check Workflow Run Logs via CLI

```bash
# List recent runs
gh run list --repo owner/repo --limit 10

# Watch a live run
gh run watch <run-id>

# View logs for a specific run
gh run view <run-id> --log

# Re-run a failed job
gh run rerun <run-id> --failed
```

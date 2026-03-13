# GitHub Actions Workflow Reference

Quick field-by-field guide for writing and reading `.github/workflows/*.yml` files.

---

## Top-Level Keys

```yaml
name:        # Display name in the Actions tab
on:          # Trigger events (push, pull_request, schedule, workflow_dispatch, etc.)
permissions: # Restrict default GITHUB_TOKEN permissions (principle of least privilege)
env:         # Workflow-level environment variables
jobs:        # One or more named jobs
```

---

## Trigger Events (`on:`)

```yaml
on:
  push:
    branches: ["main"]          # Only on pushes to main
    paths: ["src/**"]           # Only when these paths change

  pull_request:
    types: [opened, synchronize]

  schedule:
    - cron: "0 9 * * 1"         # Every Monday 09:00 UTC

  workflow_dispatch:            # Manual trigger from Actions tab
    inputs:
      environment:
        description: "Target env"
        required: true
        default: "staging"
```

---

## Job Structure

```yaml
jobs:
  my-job:
    name: Friendly display name
    runs-on: ubuntu-latest      # Runner: ubuntu-latest, windows-latest, macos-latest
    timeout-minutes: 15         # Kill job if it hangs
    needs: [other-job]          # Run after another job completes
    if: github.ref == 'refs/heads/main'  # Conditional execution

    steps:
      - uses: actions/checkout@v4

      - name: Step name
        run: echo "hello"
        env:
          MY_VAR: ${{ secrets.MY_SECRET }}
```

---

## Strategy Matrix

```yaml
strategy:
  fail-fast: false
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
    os: [ubuntu-latest, macos-latest]
    exclude:
      - os: macos-latest
        python-version: "3.10"

# Reference matrix values in steps:
runs-on: ${{ matrix.os }}
```

---

## Contexts and Expressions

```yaml
${{ github.actor }}          # User who triggered the run
${{ github.ref }}            # Branch/tag ref, e.g. refs/heads/main
${{ github.sha }}            # Commit SHA
${{ secrets.MY_SECRET }}     # Encrypted secret
${{ env.MY_VAR }}            # Environment variable
${{ steps.step-id.outputs.result }}  # Output from a previous step
```

---

## Common Actions

| Action | Version | Purpose |
|--------|---------|---------|
| `actions/checkout` | v4 | Clone the repository |
| `actions/setup-python` | v5 | Install Python |
| `actions/setup-node` | v4 | Install Node.js |
| `actions/cache` | v4 | Cache dependencies |
| `actions/upload-artifact` | v4 | Save build outputs |
| `actions/github-script` | v7 | Run JS against GitHub API |

---

## Permissions (Least Privilege)

```yaml
permissions:
  contents: read       # Default — read repo files
  issues: write        # Needed to create/label issues
  pull-requests: write # Needed to comment on PRs
  packages: write      # Needed to publish to GHCR
```

Always declare only the permissions your workflow actually needs.

---

## Useful Tips

- Use `workflow_dispatch` on every scheduled workflow so you can test it manually.
- Pin action versions to a commit SHA in production for supply chain security.
- Use `$GITHUB_STEP_SUMMARY` to write markdown into the job summary panel.
- Set `timeout-minutes` on every job to prevent billing surprises on runaway jobs.

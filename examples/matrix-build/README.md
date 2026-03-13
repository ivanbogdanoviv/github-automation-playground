# Example: Matrix Build

Shows how to run CI across multiple operating systems and runtime versions in parallel using a `strategy.matrix`.

## Key Concepts
- `matrix.os` / `matrix.node-version` — define the axes
- `fail-fast: false` — let all combos run even if one fails
- `exclude` — skip specific combinations

## How to use
Copy `workflow.yml` to your repo's `.github/workflows/` and adjust the matrix values and build steps for your stack.

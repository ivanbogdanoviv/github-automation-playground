# Example: Scheduled Job

Template for a workflow triggered by a cron schedule, with a `workflow_dispatch` manual trigger for easy testing.

## Key Concepts
- `schedule.cron` — standard 5-field cron expression (UTC)
- `workflow_dispatch` — lets you trigger manually from the Actions tab
- `inputs` — optional parameters when triggering manually (e.g. dry_run flag)
- `timeout-minutes` — safety cap to prevent runaway jobs

## How to use
1. Copy `workflow.yml` to `.github/workflows/`
2. Update the cron expression and replace the "Do the work" step
3. Test by clicking **Run workflow** in the Actions tab before waiting for the schedule

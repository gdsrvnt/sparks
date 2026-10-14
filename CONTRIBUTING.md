# Contributing

## Priority labels

Every issue, and every open (non-draft) pull request, must carry exactly one priority label:

| Label | Color |
|---|---|
| `low` | very pale yellow (`#FFFBE6`) |
| `medium` | yellow (`#FBCA04`) |
| `high` | orange (`#FF8C00`) |
| `urgent` | red (`#D73A4A`) |

Draft PRs may carry one but need not. The `priority-label` workflow (`.github/workflows/priority-label.yml`) enforces this: it fails until exactly one priority label is present, and on issues it comments once asking for one. GitHub cannot block creation itself, so the failing check is the gate. A failure names the labels it found, what to change, and a `gh` command for it, in the check's annotation and job summary. The check reads the current labels, so changing a label (which re-runs it) or re-running it by hand clears it once the labels are right.

If the requester names a priority, use it. Otherwise pick one with your best judgment. Pull request text: [AGENTS.md](AGENTS.md).

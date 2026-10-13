# Contributing

## Priority labels

Every issue, and every open (non-draft) pull request, must carry exactly one priority label:

| Label | Color |
|---|---|
| `low` | very pale yellow (`#FFFBE6`) |
| `medium` | yellow (`#FBCA04`) |
| `high` | orange (`#FF8C00`) |
| `urgent` | red (`#D73A4A`) |

Draft PRs may carry one but need not. The `priority-label` workflow (`.github/workflows/priority-label.yml`) enforces this: it fails until exactly one priority label is present, and on issues it comments once asking for one. GitHub cannot block creation itself, so the failing check is the gate.

If the requester names a priority, use it. Otherwise pick one with your best judgment.

# Linear Tickets

## What this source contains

- Issues describing features, bugs, and their motivation
- Project docs attached to issues (often PRDs or specs)
- Parent/sub-issue relationships (broader initiative → specific tickets)
- Comments on issues (clarifications, scope changes, "why we're doing this" rationale)
- Labels (e.g., `compliance`, `customer-request`, `perf`) that signal the type of motivation
- Status updates that explain scope changes
- Attachments and linked GitHub PRs

## How to search it

Use the Linear MCP.

1. **Start with linked tickets.** If the seed commits or PRs reference ticket IDs (e.g., `ENG-1234`, `[BUG-567]`), fetch those first with `get_issue`. Read the full issue including comments.
2. **List related issues by keyword.** Use `list_issues` with text search for the feature name, key symbol, or business term. Try multiple phrasings.
3. **Walk the issue tree.** If you land on a sub-issue, fetch its parent.
4. **Read project docs.** If the issue belongs to a project, use `get_project` and check attached docs.
5. **Check labels and milestones.**

## What good evidence looks like here

- An issue description stating the business problem: "Customer Acme needs X because of their SOC2 audit"
- A comment recording a decision: "We decided to go with approach B because approach A would require touching the billing service"
- A parent issue titled like an initiative: "Q3 Enterprise Readiness" or "Reduce Payment Failures"
- An attached PRD or spec
- Labels like `customer:acme`, `incident-followup`, `compliance`, `perf-regression`

## Common pitfalls

- **Scope drift.** The ticket the PR references may have been closed and reopened with a different scope. Read the whole history.
- **Reading intent.** Follow the intent guidance for this source, appended to your prompt from Sparks' `docs/uncovering-intention.md`.
- **Stale tickets.** Old tickets often reflect a version of the plan that changed. Check dates and cross-reference with the code's ship date.
- **Closed-as-duplicate chains.** Follow the duplicate-of relationships back to the canonical ticket.
- **Private workspace content.** If you can't access an issue, note that as a gap rather than guessing.

## What to return

For each relevant ticket:
- Ticket ID and title
- The problem/motivation quoted from the description or comments (not paraphrased. The synthesizer needs the exact text to cite)
- Labels, parent issue, project
- Author, created date, closed date
- Link to the ticket if available

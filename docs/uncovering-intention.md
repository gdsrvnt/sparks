# Uncovering intention (draft)

How to tell why code came to be the way it is, as opposed to what it does. Everything below except the headings and the *From* notes is by Lauren Tan ([@poteto](https://github.com/poteto)), moved word for word out of the investigator playbooks of the bundled `why` skill (`skills/why/references/`, from pstack at commit `118e73b`). It is used under the MIT License, Copyright (c) 2026 Lauren Tan; see [`skills/LICENSE-poteto`](../skills/LICENSE-poteto) and [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md). Headings and *From* notes are Sparks additions. The `why` skill pastes the section for each investigator's source, plus the first section, into that investigator's prompt.

## Reading intent from evidence

*From `investigator-prompt.md`.*

- **Mechanics are not motivation.** A commit changing `limit = 50` to `limit = 100` shows the change, not necessarily why. Look for the reason in the commit message, PR description, linked ticket, or review comments.
- **No intent from code behavior or style.** You may read code to learn what the target *is*. "The author chose a functional approach" is an observation about code, not evidence of intent. Claim intent only where the author stated it.

## What runtime telemetry says about intent

*From `sources/datadog.md`.*

> A metric's *presence* is itself evidence that someone thought the number worth watching.

> A monitor firing on `rate_limit_hit > 10/min` is direct evidence the team worried about that threshold.

> The threshold is frequently the answer to "why is this clamped at N?"

- **Correlation is not causation.** A spike before a PR and stabilization after is suggestive, not definitive, since other changes may have landed in the same window. Check neighboring PRs.
- **Overfitting to the chart you found.** A chart reflects its maker's framing. A chart named "retry success rate" is evidence the team cared about retry success, not that it's why a specific line of code exists.
- **Instrumented != caused.** A metric shows someone cared enough to measure something, not that the code was added *because* of it. Cross-reference with commit/PR dates.

> An incident whose timeline includes "added defensive check for X" is near-direct evidence.

## What warehouse data says about intent

*From `sources/databricks.md`.*

- **Instrumented ≠ caused.** An event's existence means someone cared enough to log it, not that the target code exists *because* of it. Pair with a PR/commit citation from the git investigator before claiming causation.

> Upstream changes frequently motivate consumer-code changes.

> A p99 that matches the target's threshold constant suggests the number was chosen from data.

## Where the business why lives in tickets

*From `sources/linear.md`.*

> Linear is where the product/business context often lives: the "we're doing this because customer X asked" or "this is for the Q3 compliance initiative" layer.

> Sub-issues are tactical. Parents often carry the "why."

> Milestones tie work to deadlines, which often reveal motivation.

- **Mechanical templates.** Some teams require "Why" sections but fill them with boilerplate. Generic text ("improve user experience") is probably not a real answer.

> Project-level documents are where specs and rationale are most often captured.

> Labels hint at the category of motivation (customer-request, incident-followup, compliance).

## Where the long-form why lives

*From `sources/notion.md`.*

> Notion is where "why" often lives in long-form before it becomes code. A significant feature usually has a doc.

- **Boilerplate templates.** Some orgs require a "Why" section that gets filled with fluff. Look for specificity.

## Telling a decision from chatter

*From `sources/slack.md`.*

- **Speculative jokes as "decisions."** Slack is casual. "Lol just do the thing" isn't a decision, even if it preceded the commit. Look for considered discussion.

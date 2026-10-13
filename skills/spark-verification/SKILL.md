---
name: spark-verification
description: "Create or maintain a project-local verification skill with the project's sparks as ammunition, by running poteto's create-verification-skill or maintain-verification-skill. Headless mode reads every spark; interactive mode first runs sparks-discuss with the user, then improves the skill from the sparks just written. Use for /spark-verification or \"verify against sparks\"."
disable-model-invocation: true
---

# Spark verification

Sparks are ammunition. A verification skill is the weapon. This skill is an adapter: it runs poteto's [`create-verification-skill`](../create-verification-skill/SKILL.md) when the project has no verification skill, or [`maintain-verification-skill`](../maintain-verification-skill/SKILL.md) when it has one, and loads the human intent in `sparks.json` into it. Both are bundled in this plugin. Open the file and follow that skill as written. This file adds only what sparks change.

## Pick the mode

- **Headless**: nobody is there to answer (a scheduled or CI run, print mode), or the user says `headless`.
- **Interactive**: a user is there and didn't say headless.

## Load the sparks

Find every `sparks.json` in the repo, git-ignored ones included (`find . -name sparks.json -not -path './.git/*'`). They apply project-wide by default. A file that doesn't parse or doesn't match the plugin's [`spark.schema.json`](../../spark.schema.json) stops the run: report it, and never fix it by hand. No `sparks.json` at all: headless stops and points at `/sparks-discuss`; interactive starts there.

## Sparks as ammunition

Sparks outrank inferred priorities. Read each spark for what it decides about verification; one spark can decide several things.

- **Coverage**: a feature, surface, or user path that matters becomes a feature in the map. Features come from coverage sparks first, then from source for top surfaces the sparks miss.
- **Proof**: what "working" means (an output, a state, a side effect, a speed, a look) becomes an end-state check.
- **Path**: a route, entry point, platform, or condition that must be exercised becomes a required drive step. A proof that skips it is incomplete.
- **Prohibition**: a hard don't or something to be wary of (often `R`) becomes a `Never:` line in the skill and a gotcha in any feature it bites. Keep the spark's words; don't soften them.
- **Context**: stack, packaging, or knowledge sources (often `S` or `K`) inform Launch, Doctor, and Drive.
- **None**: no bearing on verification. Leave it out.

End each line a spark decides with `[spark: "<exact question>"]`. The question is what `sparks entry add` replaces by, so the citation survives a revised answer. A line with no citation is inferred from source; that's allowed.

Where the upstream skill would ask the user, answer from the sparks first. Where the code and a spark disagree, don't pick a side silently: report the conflict (what the spark says, what source shows, where). An app that breaks a proof or prohibition spark is a product gap: put it at the top of the report with the spark and the evidence, and keep product code out of the change.

## Headless

1. Read every record in every `sparks.json`, thoroughly.
2. Run create or maintain, and place every spark. Several verification skills and no one to ask which: stop and report.
3. When maintaining, the coverage audit also lists sparks that decide something but have no citation (place them, or say why they can't be verified), citations whose question no longer exists (find the reworded spark, or drop the tag), and uncited lines (leave them; they're candidates for `/sparks-discuss`).
4. What only the user could answer goes in the report as a question for `/sparks-discuss`. Don't guess.

## Interactive

1. Run a sparks-discuss session with the user ([`../sparks-discuss/SKILL.md`](../sparks-discuss/SKILL.md)) aimed at verification: what working means, which paths must be exercised, what must never happen, and why the skill's uncited lines are there. The user deepens existing sparks or adds context that isn't in any spark yet. Every sparks-discuss rule holds, and only the user ends it.
2. Take the entries that session wrote, new or replaced, as the priority. No verification skill yet: create one as headless does, those entries first. Otherwise run maintain with those entries first: place each one and update every line that cites a question whose answer changed.
3. Trust that the older sparks are already in the skill. Don't re-audit them. Read an older spark only where a new entry replaces, extends, or contradicts it.

## Scope and report

Edit only what the upstream skill lets you edit. `sparks.json` changes only through sparks-discuss, with the user; headless never edits it.

Add to the upstream report: the mode, the sparks placed, conflicts, spark violations, sparks that can't be verified and why, uncited lines, and questions for `/sparks-discuss`.

Adapted from poteto's skills, which are bundled with their license; see [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).

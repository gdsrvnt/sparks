---
name: spark-verification
description: "For a PR or branch, verify every changed file against the sparks.json answers that apply to its directory. Read-only: report violations with the file and the quoted spark; never edit code or open PRs. Use for /spark-verification or \"verify against sparks\"."
disable-model-invocation: true
---

# spark verification

Verify that the files in a pull request or branch still honour the project's sparks. This skill is read-only: it reports violations and never edits product code, never edits `sparks.json`, and never opens pull requests.

## Scope

Work on one PR or one branch at a time. The base is the PR base branch, or `main` when verifying a branch with no PR.

## Steps

1. **List the diff.** Against the base, list every file added, modified, or deleted (paths relative to the repo root). Deleted files still count: check whether the deletion itself breaks a spark.
2. **Collect applying sparks.** For each changed file, look in that file's directory for a `sparks.json` list of sparks. Also note every `sparks.json` in ancestor directories up to the repo root. Per the [README](../../README.md) convention, `sparks.json` files in any directory apply globally to a project by default; the user decides if and how to scope them. Report which files you loaded and whether you treated ancestor files as in scope (default: yes, globally).
3. **Parse.** A `sparks.json` that does not parse or does not match the plugin's [`sparks.schema.json`](../../sparks.schema.json) stops the run for that file: report the path and the error, and never fix it by hand.
4. **Verify.** For each changed file, read the file (or the deletion) against every loaded spark's answer. A violation is any place the change contradicts, softens, or ignores what a spark's answer requires. Prefer the spark's own words over paraphrase.
5. **Report.** For each violation, name the file path and quote the spark (question and answer, or at least the answer). Group by file. If nothing violates, say so in one line. End with a short count: files checked, sparks loaded, violations found.

## Out of scope

- Creating or maintaining a project-local verification skill.
- Running `create-verification-skill` or `maintain-verification-skill`.
- Headless or interactive modes that edit the tree or open PRs.
- Editing product code to "fix" a violation. Report only; the user decides what to do next.

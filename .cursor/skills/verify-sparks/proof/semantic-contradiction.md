# Proof: semantic contradiction

Notes from one end-to-end drive of this skill. Not a normative claim. The evidence directory is outside the checkout; this file quotes the run. File and command names follow the current helper and tree (`sparks add`, `add.txt`, `sparks.json`, `sparks.schema.json`).

Commands, from the repository root, after `export PATH="$PWD/.cursor/skills/verify-sparks/scripts:$PATH"`:

```text
check-verify-sparks doctor
check-verify-sparks contradict --out <evidence>
check-verify-sparks add --out <evidence>
check-verify-sparks herdr-snapshot --out <evidence>
```

Then the prose pass wrote `prose.md` in that evidence directory. `check-verify-sparks cleanup --out <evidence>` removed 0 scratch directories. `prose.md`, `report.txt`, `add.txt`, `add-file.json`, and `herdr-snapshot.txt` were still there after cleanup.

Doctor ended with `doctor: OK`. HEAD at the run was `7fa1afc` with a dirty tree (this skill and the test cuts, not yet committed).

Script summary after `contradict` and `add`:

```text
summary: 6 pass, 0 fail -> PASS
script-pass is not a verification pass; prose.md is still required
```

That script pass is structural only (schema set, optional id, skill frontmatter names, example id, official XXH64 vectors, isolated `sparks add`). It does not clear the prose findings below.

Herdr drive, isolated `--db`, stdout counts matched a read-only sqlite open: workspaces 6, tabs 40, panes 40, agents 17. The default herdr database was not opened.

A throwaway clone with `id` added to the schema required set, and `spark_id.TYPES` changed to include `x` and drop `k`, was checked with `--repo` and then deleted. The helper loaded that clone's modules and reported both `FAIL`s. It did not report them against this checkout.

Prose findings, quoted from the pass (not fixed in this change):

- `CHANGELOG.md` under `## [Unreleased]` says type must be `S`, `P`, `A`, `R`, or `K`. `sparks.schema.json` and README require lowercase `s`, `p`, `a`, `r`, `k`.
- The same Unreleased Added section still describes `spark-verification` as the create/maintain adapter. The Changed bullet, the skill, and README say it is read-only.
- The same Unreleased Added section still names `use-herdr`. The Changed bullet and the tree say `herdr-operations`.

Post-call ownership, blocker clearing, and the read-only verification skill agree across the current rule, skill, and README files.

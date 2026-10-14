# Spark records

`spark.json` at the root is the canonical example, and `spark.schema.json` is its schema. Spark records extracted for development live as `sparks.json` files on the `sparks/development-main` branch. They are tracked there and never on `main`.

## Sub-features

- `canonical-valid`: root `spark.json` validates against `spark.schema.json`.
- `no-extra-on-main`: on any branch other than `sparks/development-main`, any other tracked `spark.json` or `sparks.json` is `FAIL`.
- `dev-branch-valid`: if `sparks/development-main` or `origin/sparks/development-main` exists, every `sparks.json` on it is read with `git show <ref>:<path>` and validated. There is no checkout. The branch with no `sparks.json` is `WARN`, and a missing branch is `SKIP`.

## How to get to it (user POV)

- `bin/sparks entry add` writes `sparks.json` in the current directory (see README). Contributors commit those on the development branch.

## Driving it with check-sparks-hygiene

- `git fetch origin && check-sparks-hygiene run --only sparks-files`.
- Without the branch: `SKIP sparks/development-main not present locally or as origin/sparks/development-main`.
- Negative proof: in a throwaway clone, create `sparks/development-main` with a committed `sparks.json` of `[{"type":"Z","question":"q"}]`, then switch back. The check reports `FAIL sparks/development-main:sparks.json: 0: missing 'answer'` and `... 0.type: 'Z' not in [...]`.

## Gotchas

- Without `jsonschema` installed, validation uses the rules read from `spark.schema.json`. They cover that schema completely today. If the schema grows, install `jsonschema` to get full validation.
- Only local refs are read. Run `git fetch origin` first, or a stale or missing remote ref is checked instead.

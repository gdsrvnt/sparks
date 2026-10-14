# sparks verification map

This directory is the maintained source for verifying the sparks repository. Read the index before driving, then use the matching feature file as the recipe.

Semantic contradiction across the whole source is the precedent. Programmatic drives are allowed. They do not replace the prose pass in [semantic contradiction](./semantic-contradiction.md).

## Baseline preconditions

- The checkout is the sparks repo (`sparks.schema.json` and `bin/sparks` exist).
- `python3` >= 3.11, `git`, and `uv` are on `PATH`.
- `check-verify-sparks` is on `PATH` (`export PATH="$PWD/.cursor/skills/verify-sparks/scripts:$PATH"`).
- `check-verify-sparks doctor` ended with `doctor: OK`.
- Evidence is outside the checkout (`~/.local/state/verify-sparks/` or `--out`).
- CLI drives use a temp directory the helper creates. Never drive the user's `sparks.json` or the default herdr database.

## Driving conventions

- Start every recipe from the baseline state.
- Treat every command as literal. Keep flags and quoted strings unchanged.
- Run decidable checks through `check-verify-sparks contradict`.
- Run the CLI through `check-verify-sparks add`, `check-verify-sparks herdr-snapshot`, or `check-verify-sparks agent-spawn`, not by hand against a shared file.
- The prose pass reads every path under `# normative` and `# implementation` in `index.txt`. `# evidence-not-normative` is not a claim. A normative file missing from that index was not verified.
- Do not report a skipped entry point as verified through a different path.

## Proof and skip reporting

- Capture the command, stdout, stderr, and exit code for every helper command.
- A contradiction proof quotes both claims and names both files. A clean file is `none`, not an omitted file.
- `FAIL` means the check found a contradiction. Do not edit the checkout to turn a `FAIL` into a `PASS` during verification.
- `UNREACHABLE` (exit 3) names the prerequisite and the command that was attempted.
- Proof artifacts stay after cleanup. Cleanup removes scratch directories only.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior. It then uses exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every user entry point.
3. `Driving it with check-verify-sparks` starts with `Preconditions:` and uses labeled bullets that pair each user action with an exact command and observable result.
4. `Gotchas` lists traps that can waste or invalidate a verification run.

## Features

- [Semantic contradiction](./semantic-contradiction.md) is the precedent: source-wide claims in README, docs, schema, rules, and first-party skills.
- [Add](./add.md) covers `sparks add [--path]`: create, exact-question replace, and a refusal that does not write. There is no `entry add`.
- [Id and hash](./id-and-hash.md) covers the published XXH64 vectors and every stored id in the root `sparks.json`.
- [Herdr snapshot](./herdr-snapshot.md) covers an isolated `sparks herdr snapshot --db`.
- [Agent spawn](./agent-spawn.md) covers `sparks agent spawn --dry-run`: a persona's pi command, an unknown type, and a smuggled flag. It never launches.

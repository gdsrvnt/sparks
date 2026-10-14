---
name: verify-sparks
description: "Verify the gdsrvnt/sparks repo itself: source-wide semantic contradiction across README, docs, schema, rules, and first-party skills is the precedent, with a small programmatic helper for the XXH64 vectors and the sparks add path. Use before a PR, or when the pytest suite is being treated as the spec."
disable-model-invocation: true
---

# Verify sparks

This skill replaces the pytest suite as the way to verify this repository. sparks is a semantic project: the spec is the prose. A test that restates a sentence, or that computes both sides with the same function, is not verification.

`spark-verification` is a different skill. It checks a PR diff against `sparks.json` answers and stays read-only. This skill checks the sparks repository's own sources against each other. It does not edit the checkout and it does not open pull requests.

## Strategy

Precedent, in order:

1. **Source-wide semantic contradiction.** Read every path under `# normative` and `# implementation` in `index.txt`. Skip `# evidence-not-normative`. A contradiction is two current claims that cannot both be true, or a current claim the code breaks. Quote both sides. Historical changelog sections under a version heading are not current; `## [Unreleased]` is current. Vendored skills (`ketchup`, `how`, `why`, `bro`, `show-me`, `create-verification-skill`, `maintain-verification-skill`) are not sparks' claims; do not grade their internals. A diff-only pass is incomplete.
2. **Decidable cross-file checks.** `check-verify-sparks contradict` compares the schema enum set with `spark_id.TYPES`, checks that `id` is not required, checks skill frontmatter names, pins the example spark's stored id, and checks the published XXH64 vectors. It does not parse English. These checks do not replace the prose pass. A script `PASS` is not a verification pass.
3. **One user path.** `check-verify-sparks add`, `herdr-snapshot`, and `agent-spawn` drive `bin/sparks` the way a user does, in a temp directory. They are not a matrix of injected `OSError`s, signals, or lock timings. Do not add those back as pytest.

Do not grow `tests/`. A new semantic claim belongs in this skill's prose pass. A new mechanical contract belongs in the helper only when it has an independent oracle or a user-visible failure the prose pass cannot see. Phrase locks (the file contains the sentence we wrote) are not contracts.

## Launch

No process is left running, and this skill does not start herdr. `herdr-snapshot` needs a herdr server that is already running; if it is not, that drive is `UNREACHABLE`, not a pass. `agent-spawn` needs `pi` on `PATH` with at least one listed model, and never starts herdr or an agent. Needs `git`, `python3` >= 3.11, and `uv` on `PATH`. `bin/sparks` is a uv script. The first `uv run --script bin/sparks` installs `jsonschema` into the uv cache, not into the checkout. The helper sets `UV_CACHE_DIR` and `PYTHONDONTWRITEBYTECODE` so that cache stays outside the checkout. Ready means `doctor` prints `doctor: OK`.

From the repository root:

```bash
cd <repo-root>
export PATH="$PWD/.cursor/skills/verify-sparks/scripts:$PATH"
check-verify-sparks doctor
```

Each drive uses a scratch directory under `/tmp/verify-sparks-scratch` (or `~/.local/state/verify-sparks-scratch` if `/tmp` is inside the checkout). The helper does not honor `TMPDIR` for that scratch. Never point a drive at the user's `sparks.json` or at the default herdr database (`$SPARKS_HERDR_DB` or `~/.local/share/sparks/herdr-state.sqlite`).

## Doctor

```bash
check-verify-sparks doctor
```

Read-only. It does not install packages and does not launch the CLI. Last line is `doctor: OK` or `doctor: FAIL`. It checks Python >= 3.11, `uv`, `git`, and that `sparks.schema.json`, `bin/sparks`, `spark_id.py`, `spark_hash.py`, and `README.md` exist. It prints `HEAD` and whether the tree is dirty. A dirty tree is not a failure: the checks read the working tree. Run doctor again after any failed drive before driving something else.

## Drive

```bash
check-verify-sparks contradict          # decidable claims + index.txt
check-verify-sparks add                 # isolated CLI round-trip
check-verify-sparks herdr-snapshot      # isolated --db; never the default database
check-verify-sparks agent-spawn         # dry runs against pi's model list; never launches
check-verify-sparks run                 # contradict + add
check-verify-sparks contradict --repo /other/checkout --out /tmp/out
```

| Command | What it proves | Feature file |
| --- | --- | --- |
| `contradict` | schema enum set vs `spark_id.TYPES`, optional id, skill frontmatter names, example id, official XXH64 vectors; writes `index.txt` for the prose pass | [semantic contradiction](features/semantic-contradiction.md) |
| `add` | create a file, refuse invalid JSON without writing, replace by exact question and keep the stored id | [add](features/add.md) |
| `herdr-snapshot` | `sparks herdr snapshot --db <temp>` against a running herdr, or `UNREACHABLE` with the missing prerequisite | [herdr snapshot](features/herdr-snapshot.md) |
| `agent-spawn` | `sparks agent spawn --dry-run` plans the pi command (with the api-error extension and the sparks prompt) for a persona built from `pi --list-models`, refuses an unknown type and smuggled `--model` and `--tools`, and checks the shipped `reviewer`; `UNREACHABLE` without pi | [agent spawn](features/agent-spawn.md) |
| vectors inside `contradict` | published XXH64 sanity-check rows, not a digest computed by `spark_id` | [id and hash](features/id-and-hash.md) |

Exit `0` when this command's decidable checks passed, `1` on any `FAIL` from this command, `2` on usage errors, `3` when herdr snapshot or agent spawn is unreachable. `add`'s exit code is only that command; if it merges into an existing report, the printed summary can still be `FAIL` from an earlier check. A merge is refused when the existing report is a different repo or `HEAD`. `UNREACHABLE` is not a pass and is not counted in the summary as `PASS`.

A `FAIL` is a successful verification run that found a contradiction. Do not weaken a check to make it pass. `summary: ... PASS` is a script pass only. The line `script-pass is not a verification pass` means `prose.md` is still required.

The prose pass is not optional on `contradict` or `run`. After the script writes `index.txt`, read every path under `# normative` and `# implementation`. Paths under `# evidence-not-normative` are not claims. Write `prose.md` in the evidence directory, one heading per normative and implementation path. A script-only run has not verified the repository. Vendored skill bodies are not in the index.

## Evidence

Evidence path, first match: `--out`, then `$VERIFY_SPARKS_EVIDENCE`, then `~/.local/state/verify-sparks/<stamp>-<head>/`. The path is resolved before the checkout check. The script refuses a path inside the checkout, a symlink evidence directory, or a symlink artifact (`report.txt`, `prose.md`, `scratch.txt`, and the other names in the helper). `--repo` loads `spark_hash.py` and `spark_id.py` from that checkout, not from the helper's own tree.

A proof includes `report.txt`, `report.json`, `index.txt`, and `prose.md`. CLI drives also leave `add.txt`, `herdr-snapshot.txt`, or `agent-spawn.txt` with argv, cwd, exit code, and both streams. Herdr proof includes the read-only sqlite counts. Quote the summary line, every `FAIL`, the `HEAD`, and whether doctor said the tree was dirty.

To prove a decidable check catches a contradiction, plant it in a throwaway clone (`git clone -q . "$tmp"`), run `check-verify-sparks contradict --repo "$tmp" --out <evidence>/negative`, and delete the clone. Never plant it in the checkout.

## Cleanup

```bash
check-verify-sparks cleanup --out <evidence-dir>
```

Removes only scratch directories this run created: absolute paths under the scratch parent that contain `.verify-sparks-scratch`. It refuses the checkout, the evidence directory, the default herdr database, relative paths, and anything without that marker. A line is dropped only after the directory is gone. Does not remove the evidence directory. The add and herdr drives already delete their scratch on the way out; cleanup is for a drive that died first. Never kill by process name. This skill starts no long-lived process.

## Helpers

`scripts/check-verify-sparks` is the only helper. It is executable and uses the Python standard library plus `uv` to launch `bin/sparks` and `spark_id.py`. Invocation is the commands in Drive. It does not write into the checkout.

## Maintenance

When the prose, the schema, or the CLI contract changes, run `/maintain-verification-skill` against this skill. Edit only `.cursor/skills/verify-sparks/`. A behavior the map describes that the repo no longer has is either map drift or a product gap; do not paper over a product gap by weakening the map.

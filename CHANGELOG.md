# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `.cursor/skills/verify-sparks/`: project-local verification skill generated from the bundled `create-verification-skill`. Source-wide semantic contradiction is the precedent. `scripts/check-verify-sparks` checks decidable cross-file claims, the published XXH64 vectors, and one isolated `sparks add` path. It does not replace `spark-verification`.

### Changed

- A typed question-and-answer pair is a spark, the primitive; `sparks.json` is a list of sparks. The command is `sparks add [--path <path>]`, and `--path` defaults to `./sparks.json`. There is no `spark add` or `entry add` command. The example file is `sparks.json` and the schema file is `sparks.schema.json`. Prose lowercases spark and sparks except the type letters S, P, A, R, and K, their names, and `SPARK.db`. Internal identifiers use spark terminology (`parse_spark`, `spark_json`, `spark_id`). The JSON shape, ids, and add behavior are unchanged. Verbatim quotations, `docs/vision-transcript.md`, licenses, and xxHash credits are unchanged; the sparks-domain description in `THIRD_PARTY_NOTICES.md` now names `sparks add`.
- `study` playbooks re-derived from the source video (issue #22). Each playbook gains a `## Rationale` section on why the role exists and where it sits in the chain. The other sections are no longer than before. They now carry lessons the first summary missed, such as the 10-15% unaided redo and recall-over-rereading.
- `study` `SKILL.md` gains an `## Order` section with each role's needs and hand-offs. It explains why the examiner follows the listener and why the diagnostician waits for the same failure mode twice. The session log now records performance conditions, skips, the plan, and each miss with its reason.
- `.github/workflows/priority-label.yml`: a failure now says which issue or PR, what labels it has, and what to change: `Missing priority label` or `Too many priority labels` as the annotation title, plus a job summary with the triggering event, the rule, and a `gh` fix command. Before, it said only `found 0` ([#71](https://github.com/gdsrvnt/sparks/pull/71)). It reads the current labels instead of the event snapshot, so a manual re-run after a fix passes. If it cannot read them, it warns and falls back to the snapshot. It sums the comment-marker count with `jq` instead of `bc`.
- Ids are back as an optional `id` key in `sparks.schema.json` (`^[0-9a-f]{16}$`). `bin/sparks add` computes it on insertion and writes it; a replacement keeps a stored id. The hash is XXH64 (seed 0) over the same preimage, from the new dependency-free `spark_hash.py` (pure standard library), replacing SHA-256. Files without ids stay valid.
- Verification of this repo is the `verify-sparks` skill, not the pytest suite. Removed tautologies and near-tautologies from `tests/test_sparks.py` and `tests/test_spark_hash.py` (phrase locks on skills and rules, duplicate id/hash assertions, an internal `derive_id` call probe, and overlapping herdr type cases). The remaining tests are the mechanical kernel only.
- `skills/spark-verification/SKILL.md`: replaced the create/maintain adapter (headless and interactive modes that could edit the tree or open PRs) with a short read-only skill that verifies every file in a PR or branch diff against the `sparks.json` files that apply to each changed file's directory, reporting violations with the file and the quoted spark. Old skill parked on branch `spark-verification-rework` ([#56](https://github.com/gdsrvnt/sparks/issues/56); [Discussion #45](https://github.com/gdsrvnt/sparks/discussions/45)). Updated `README.md`, `THIRD_PARTY_NOTICES.md`, and the `sparks-discuss` hand-off.
- `skills/spark-voice/SKILL.md` hang-up: instead of only telling the user to run `sparks-postcall`, open that skill's `SKILL.md` and follow it (or ask for `/sparks-postcall` if unreadable), and hand it the transcript paths. The post-call protocol still lives only in `sparks-postcall`.
- Renamed `skills/use-herdr/` to `skills/herdr-operations/` (frontmatter `name: herdr-operations`). Updated references in `skills/sparks-postcall/SKILL.md` and `README.md`.
- `sparks.schema.json`: `type` must be one of `S`, `P`, `A`, `R`, or `K`. `sparks.json`, `spark_id.py`, and `bin/sparks` follow that shape.

### Removed

- `skills/teach/`, with its `THIRD_PARTY_NOTICES.md` entry. Parked on branch `teach-rework` for rework before re-merging ([#51](https://github.com/gdsrvnt/sparks/issues/51)). Findings from [Discussion #45](https://github.com/gdsrvnt/sparks/discussions/45): depends on nonexistent `unslop`, calls `how`/`why` with model invocation disabled, asks `why` for a narrow run it does not allow.
- `.github/workflows/upstream-tracker.yml`, `.github/upstreams.json`, and `.github/upstream-check.sh`. We no longer track upstream skill sources daily.
- `skills/grill-me/`, with its `THIRD_PARTY_NOTICES.md` entry. `sparks-discuss` and `sparks-domain` still derive from Matt Pocock's work and keep his credit and `skills/LICENSE-mattpocock`.
- `skills/study/`: tends three entities (the user, the sparks, the agent) on every turn inside one role, and names four aims (brainstorm, enhance knowledge, add to the sparks, get information out). It reads the root `sparks.json` and paths the user names into one union, quotes stored sparks verbatim unless the current playbook withholds the answer, and writes a held candidate only after the user accepts its exact type, question, answer, and path, through `bin/sparks add`. It keeps the linger-or-hop rule and a session log. The routing order and the ten playbooks are unchanged.

### Added

- Root `AGENTS.md`: the pull request description, and every pull request comment that reports work, must include an implementation overview walked through by component and file, so a reviewer can follow the change without reading the diff file by file. Priority labels stay in `CONTRIBUTING.md`, which links to that rule. `README.md` links it from Contributing. It is not a plugin rule under `rules/`.
- `docs/house/community-skills/subagent/`: Mario Zechner's `subagent` skill for Pi, copied unchanged from his [gist](https://gist.github.com/badlogic/d36e325248b68414e1c6528c6ed6b525) at revision `3d7d74a` as a community skill in the house library. A `NOTICE` next to it and `THIRD_PARTY_NOTICES.md` record the source. The gist states no license, and the `wait.ts` the skill runs is not in it. It sits under `docs/`, so the plugin does not load it ([#77](https://github.com/gdsrvnt/sparks/issues/77)).
- `bin/sparks herdr query` reads the shared herdr snapshot and prints a short tab-separated table (`summary`, `workspaces`, `tabs`, `panes`, or `agents`). It does not call herdr, does not write the database, and does not print stored fetch JSON unless `--raw` is set. A pending WAL or rollback journal is a read failure, not a stale read.
- Root `sparks.json` gains a type `k` spark whose answer is `docs/house/pi`, alongside its existing spark. The root file stays tracked; other `sparks.json` files stay ignored.
- `bin/sparks herdr snapshot [--db <path>]` calls `herdr workspace list`, `herdr tab list`, `herdr pane list`, and `herdr agent list` non-interactively and upserts a shared local SQLite database of workspaces, tabs, panes, agents, and agent statuses, and records the snapshot time. The path is `--db`, else `SPARKS_HERDR_DB`, else `$XDG_DATA_HOME/sparks/herdr-state.sqlite` or `~/.local/share/sparks/herdr-state.sqlite`. It exits nonzero with one message if herdr is missing or not running, and it never runs bare `herdr`.
- `skills/herdr-operations/`: agents refresh that database before and after herdr changes, and again around a herdr heartbeat.
- `rules/post-call-self-healing.mdc`, an always-on rule: after every voice call ends (`spark-voice` hang-up), run the `sparks-postcall` self-healing procedure in full. Because `sparks-postcall` sets `disable-model-invocation`, the rule says to open `skills/sparks-postcall/SKILL.md` and follow it, or ask the user to run `/sparks-postcall`. The post-call protocol lives only in `sparks-postcall`, not in `spark-voice`.
- `.github/workflows/priority-label.yml` and `CONTRIBUTING.md`: every issue and every open (non-draft) PR must carry exactly one priority label (`low`, `medium`, `high`, `urgent`). The `priority-label` check fails otherwise, and on issues comments once asking for one. Drafts are exempt.
- `rules/blocker-clearing.mdc`, an always-on rule: when work is blocked on the user, ask one multiple-choice question with clearing options, a free-text field, and a stop-and-deliberate option that runs `sparks-discuss` and records the outcome as a spark.
- `bin/sparks add [--path <path>] --json <json>`, a uv script that adds or replaces one spark in a list of sparks in `./sparks.json` or `--path`. It checks the spark against `sparks.schema.json` and `spark_id.py`, replaces by exact decoded question regardless of type (keeping array position), appends if absent, and refuses ambiguous exact matches or an invalid existing file. Identical adds succeed without rewriting. It writes atomically, and on POSIX locks the directory so concurrent adds take turns ([#21](https://github.com/gdsrvnt/sparks/issues/21)).
- `tests/test_sparks.py`, run with `uv run tests/test_sparks.py`.
- `skills/sparks-discuss/`: interviews the user one persona at a time (study's playbooks, refit so the user is the target) and adds or replaces their answers verbatim in `sparks.json` through `bin/sparks add`. Adapted from Matt Pocock's `grilling` skill (MIT, `skills/LICENSE-mattpocock`).
- `skills/spark-verification/`: runs the bundled `create-verification-skill` or `maintain-verification-skill` with the project's sparks as ammunition, in a headless mode (every spark) or an interactive mode (`sparks-discuss` first, then the sparks it wrote).
- `skills/create-verification-skill/` and `skills/maintain-verification-skill/`, bundled unchanged from poteto's pstack at commit `118e73b`. Each has her MIT `LICENSE` next to its `SKILL.md`. Update them by copying again from pstack and updating `THIRD_PARTY_NOTICES.md`.
- `skills/sparks-domain/`: the `sparks-discuss` interview with domain modeling built in. It challenges terms against `sparks.json`, sharpens fuzzy language, stress-tests concepts with scenarios, and checks them against the code. Each settled term or decision goes into `sparks.json` through `bin/sparks add`, never into `GLOSSARY.md`, `CONTEXT.md`, or ADR files. Adapted from Matt Pocock's `domain-modeling` skill at `v1.3.1` (MIT, `LICENSE` next to its `SKILL.md`).
- `skills/sparks-postcall/`: after a call ends, extracts a spec from the transcript grounded in the user's numbered verbatim utterances, with a relay-divergence list, requirements tied to quotes, user stories with acceptance criteria, and open questions. It then gathers the work done during the call, marks each requirement met, partial, or missing with evidence, flags the call's own work that diverges from the spec, never auto-fixes verbatim or dictated content, implements gaps through `use-herdr` agents, opens PRs, has strong models review them, and merges reviewed, green, reversible changes, or names the single blocker in one numbered message. Adapted from Matt Pocock's `to-spec` skill at commit `49dd158` (MIT, `LICENSE` next to its `SKILL.md`).
- `skills/use-herdr/`: how to run coding-agent work in herdr, with Claude Code for Anthropic models and pi for xAI and OpenAI models, one agent per tab, and proactive check-ins. Includes `scripts/herdr-heartbeat.sh`, a watcher that exits when an agent finishes, blocks, stalls, or hits its time cap.
- `skills/spark-voice/`: the voice mode protocol for coding agents, for working with sparks over a phone or voice call. It is the single voice skill. The call start handshake is always on. Dictation mode is optional and turned on during a call; dictated text is saved locally at each "over" and committed only when told. The interrogation flow presents a verbatim answer, the user dictates the question, the agent reads it back and records it with `sparks add`. A voice improvement insights log is kept. Post-call work belongs to `sparks-postcall`. `sparks-discuss` runs only when no voice mode is active. The model may invoke it.

## [0.1.0] - 2026-10-12 (plugin package)

### Added

- Cursor plugin skills under `skills/`: `study` (moved from `.cursor/skills/study`), `grill-me`, and `ketchup`, `how`, `why`, `teach`, `bro` from poteto's pstack (MIT, see `THIRD_PARTY_NOTICES.md`).
- MIT license, Copyright (c) 2026 gdsrvnt.

### Removed

- Root `SKILL.md` (SPARK framing skill) and the `.cursor/skills/spark` skill with its playbooks. `README.md` supersedes them.
- `REVIEW.md`.

The plugin package version (`0.1.0`) is separate from the spark format version (`1.0.0` below).

## [1.0.0] - 2026-10-09

### Added

- A `spark.json` array of records. Each record has type `SPARK`, a question, an answer, and a 16-character id.
- `spark_id.py`, which checks those ids and unions loaded records with `connect`.
- `spark.schema.json`, which checks the shape of the array.
- `bin/spark`, a placeholder that exits 0 and writes nothing.
- `SKILL.md`, an agent framing skill that also uses the name SPARK (removed in plugin 0.1.0).
- Learning playbooks under `.cursor/skills/spark` (removed in plugin 0.1.0).

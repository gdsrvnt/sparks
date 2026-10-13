# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Renamed `skills/use-herdr/` to `skills/herdr-operations/` (frontmatter `name: herdr-operations`). Updated references in `skills/sparks-postcall/SKILL.md` and `README.md`.
- `spark.schema.json`: `type` must be one of `S`, `P`, `A`, `R`, or `K`. Records no longer have an `id` key. `spark.json`, `spark_id.py`, and `bin/sparks` follow that shape. The derived id is still printed on add, but it is not stored.

### Removed

- `skills/teach/`, with its `THIRD_PARTY_NOTICES.md` entry. Parked on branch `teach-rework` for rework before re-merging ([#51](https://github.com/gdsrvnt/sparks/issues/51)). Findings from [Discussion #45](https://github.com/gdsrvnt/sparks/discussions/45): depends on nonexistent `unslop`, calls `how`/`why` with model invocation disabled, asks `why` for a narrow run it does not allow.
- `.github/workflows/upstream-tracker.yml`, `.github/upstreams.json`, and `.github/upstream-check.sh`. We no longer track upstream skill sources daily.
- `skills/grill-me/`, with its `THIRD_PARTY_NOTICES.md` entry. `sparks-discuss` and `sparks-domain` still derive from Matt Pocock's work and keep his credit and `skills/LICENSE-mattpocock`.

### Added

- `.github/workflows/priority-label.yml` and `CONTRIBUTING.md`: every issue and every open (non-draft) PR must carry exactly one priority label (`low`, `medium`, `high`, `urgent`). The `priority-label` check fails otherwise, and on issues comments once asking for one. Drafts are exempt.
- `rules/blocker-clearing.mdc`, an always-on rule: when work is blocked on the user, ask one multiple-choice question with clearing options, a free-text field, and a stop-and-deliberate option that runs `sparks-discuss` and records the outcome as a spark.
- `bin/sparks entry add [--path <path>] --json <json>`, a uv script that adds or replaces one SPARK record in `./sparks.json` or `--path`. It checks the record against `spark.schema.json` and `spark_id.py`, replaces by exact decoded question regardless of type (keeping array position), appends if absent, and refuses ambiguous exact matches or an invalid existing file. Identical adds succeed without rewriting. It writes atomically, and on POSIX locks the directory so concurrent adds take turns ([#21](https://github.com/gdsrvnt/sparks/issues/21)).
- `tests/test_sparks.py`, run with `uv run tests/test_sparks.py`.
- `skills/sparks-discuss/`: interviews the user one persona at a time (study's playbooks, refit so the user is the target) and adds or replaces their answers verbatim in `sparks.json` through `bin/sparks entry add`. Adapted from Matt Pocock's `grilling` skill (MIT, `skills/LICENSE-mattpocock`).
- `skills/spark-verification/`: runs the bundled `create-verification-skill` or `maintain-verification-skill` with the project's sparks as ammunition, in a headless mode (every spark) or an interactive mode (`sparks-discuss` first, then the sparks it wrote).
- `skills/create-verification-skill/` and `skills/maintain-verification-skill/`, bundled unchanged from poteto's pstack at commit `118e73b`. Each has her MIT `LICENSE` next to its `SKILL.md`. Update them by copying again from pstack and updating `THIRD_PARTY_NOTICES.md`.
- `skills/sparks-domain/`: the `sparks-discuss` interview with domain modeling built in. It challenges terms against `sparks.json`, sharpens fuzzy language, stress-tests concepts with scenarios, and checks them against the code. Each settled term or decision goes into `sparks.json` through `bin/sparks entry add`, never into `GLOSSARY.md`, `CONTEXT.md`, or ADR files. Adapted from Matt Pocock's `domain-modeling` skill at `v1.3.1` (MIT, `LICENSE` next to its `SKILL.md`).
- `skills/sparks-postcall/`: after a call ends, extracts a spec from the transcript grounded in the user's numbered verbatim utterances, with a relay-divergence list, requirements tied to quotes, user stories with acceptance criteria, and open questions. It then gathers the work done during the call, marks each requirement met, partial, or missing with evidence, flags the call's own work that diverges from the spec, never auto-fixes verbatim or dictated content, implements gaps through `use-herdr` agents, opens PRs, has strong models review them, and merges reviewed, green, reversible changes, or names the single blocker in one numbered message. Adapted from Matt Pocock's `to-spec` skill at commit `49dd158` (MIT, `LICENSE` next to its `SKILL.md`).
- `skills/use-herdr/`: how to run coding-agent work in herdr, with Claude Code for Anthropic models and pi for xAI and OpenAI models, one agent per tab, and proactive check-ins. Includes `scripts/herdr-heartbeat.sh`, a watcher that exits when an agent finishes, blocks, stalls, or hits its time cap.
- `skills/spark-voice/`: the voice mode protocol for Grok Bot, for working with Sparks over a phone or voice call. It is the single voice skill. The call start handshake is always on. Dictation mode is optional and turned on during a call; dictated text is saved locally at each "over" and committed only when told. The interrogation flow presents a verbatim answer, the user dictates the question, the agent reads it back and records it with `sparks entry add`. A voice improvement insights log is kept. Post-call work belongs to `sparks-postcall`. `sparks-discuss` runs only when no voice mode is active. The model may invoke it.

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

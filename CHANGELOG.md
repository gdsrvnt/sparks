# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- `spark.schema.json`: `type` must be one of `S`, `P`, `A`, `R`, or `K`. Records no longer have an `id` key. `spark.json`, `spark_id.py`, and `bin/sparks` follow that shape. The derived id is still printed on add, but it is not stored.

### Added

- `bin/sparks entry add [--path <path>] --json <json>`, a uv script that adds or replaces one SPARK record in `./sparks.json` or `--path`. It checks the record against `spark.schema.json` and `spark_id.py`, replaces by exact decoded question regardless of type (keeping array position), appends if absent, and refuses ambiguous exact matches or an invalid existing file. Identical adds succeed without rewriting. It writes atomically, and on POSIX locks the directory so concurrent adds take turns ([#21](https://github.com/gdsrvnt/sparks/issues/21)).
- `tests/test_sparks.py`, run with `uv run tests/test_sparks.py`.
- `skills/sparks-discuss/`: interviews the user one persona at a time (study's playbooks, refit so the user is the target) and adds or replaces their answers verbatim in `sparks.json` through `bin/sparks entry add`. Adapted from Matt Pocock's `grilling` skill (MIT, `skills/LICENSE-mattpocock`).
- `skills/spark-verification/`: runs the bundled `create-verification-skill` or `maintain-verification-skill` with the project's sparks as ammunition, in a headless mode (every spark) or an interactive mode (`sparks-discuss` first, then the sparks it wrote).
- `skills/create-verification-skill/` and `skills/maintain-verification-skill/`, bundled unchanged from poteto's pstack at commit `118e73b`. Each has her MIT `LICENSE` next to its `SKILL.md`. They are not in `.github/upstreams.json`.
- A `THIRD_PARTY_NOTICES.md` entry for `skills/grill-me/` (Matt Pocock, MIT).
- The voice mode protocol for Grok Bot in `skills/sparks-discuss/references/`: `call-start-handshake.md` (the handshake, standing rules, and per-reply rules for a voice call) and `dictation-mode.md` (verbatim dictation and its `--edit` flag). A voice mode admonition at the top of `skills/sparks-discuss/SKILL.md` points to both.

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

# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `bin/sparks entry add [--path <path>] --json <json>`, a uv script that appends one SPARK record to `./sparks.json` or `--path`. It checks the record against `spark.schema.json` and the `spark_id.py` id rule, refuses a duplicate id or an invalid existing file, and writes atomically. Replace is a TODO ([#21](https://github.com/gdsrvnt/sparks/issues/21)).
- `tests/test_sparks.py`, run with `uv run tests/test_sparks.py`.

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

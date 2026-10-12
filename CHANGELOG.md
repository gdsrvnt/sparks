# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Cursor plugin scaffold: `.cursor-plugin/plugin.json` at package version `0.0.0`, a reserved empty `skills/` directory, and a `LICENSE` file stating the SPDX identifier `UNLICENSED`.
- Plugin package version stays `0.0.0` while skills are still absent. `[1.0.0]` below records the spark format, which is separate from the plugin package version.

## [1.0.0] - 2026-10-09

### Added

- A `spark.json` array of records. Each record has type `SPARK`, a question, an answer, and a 16-character id.
- `spark_id.py`, which checks those ids and unions loaded records with `connect`.
- `spark.schema.json`, which checks the shape of the array.
- `bin/spark`, a placeholder that exits 0 and writes nothing.
- `SKILL.md`, an agent framing skill that also uses the name SPARK.
- Learning playbooks under `.cursor/skills/spark`.
- A GitHub Actions workflow that checks ids and the schema on push and on pull request.

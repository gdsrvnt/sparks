# Herdr snapshot

Herdr snapshot refreshes a local SQLite file with the current herdr inventory. The user runs `sparks herdr snapshot`. Verification always passes `--db` so it cannot write the shared database.

## Sub-features

- `snapshot-isolated` runs the four list commands through `bin/sparks` into a temp database.
- `snapshot-unreachable` reports the missing prerequisite instead of calling the run a pass.

## How to get to it (user POV)

- Run `bin/sparks herdr snapshot` to refresh the default database.
- Run `bin/sparks herdr snapshot --db <path>` to name the database.
- Read the one stdout line: `snapshot <time> workspaces=<n> tabs=<n> panes=<n> agents=<n> db=<path>`.

## Driving it with check-verify-sparks

Preconditions:

- `check-verify-sparks doctor` ended with `doctor: OK`.
- The drive must not use `$SPARKS_HERDR_DB` or `~/.local/share/sparks/herdr-state.sqlite`.

- **Isolated snapshot.** Run `check-verify-sparks herdr-snapshot`. The helper sets `--db` to a file in its scratch directory. Exit `0` only if stdout is one `snapshot ` line whose counts match a read-only open of that sqlite file (`workspaces`, `tabs`, `panes`, `agents`, and the `snapshot` row). `herdr-snapshot.txt` records argv, both streams, the table counts, and the snapshot row.
- **Unreachable.** If `herdr` is missing or not running, the command exits `3`, writes `herdr-snapshot.txt`, and prints `UNREACHABLE` plus the prerequisite. That is not a pass and not a product failure.
- **Not exercised.** The default database path is not opened. Do not drop `--db` to "confirm" it.
- **Proof.** Quote the stdout line or the `UNREACHABLE` line, and the sqlite counts from `herdr-snapshot.txt`. The scratch directory is gone after the command returns.

## Gotchas

- Bare `herdr` opens a TUI. This drive never runs it. The CLI calls `herdr workspace list`, `herdr tab list`, `herdr pane list`, and `herdr agent list`.
- A pass on a temp database says nothing about the shared database. Do not open the shared one to "confirm".
- Exit `1` with some other stderr is a `FAIL`, not unreachable. Unreachable is only "not running" or "command not found".

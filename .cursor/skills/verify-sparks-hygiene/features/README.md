# Sparks hygiene verification map

The maintained source for verifying that the repository is clean and presentable. Each file covers one area: what it is, how a reader meets it, how to drive it with `check-sparks-hygiene`, and what can go wrong.

## Baseline preconditions

- Run from the repository root with `PATH="$PWD/.cursor/skills/verify-sparks-hygiene/scripts:$PATH"`.
- `check-sparks-hygiene doctor` ends with `doctor: OK`.
- For a verdict on a commit, the tree is clean. For the development branch check, `git fetch origin` has run.

## Features

| Feature | Checks | File |
| --- | --- | --- |
| Licensing and notices | `docs`, `notices` | [licensing-and-notices.md](licensing-and-notices.md) |
| Plugin manifest | `manifest` | [plugin-manifest.md](plugin-manifest.md) |
| Tracked files and .gitignore | `tracked`, `gitignore` | [tracked-files-and-gitignore.md](tracked-files-and-gitignore.md) |
| Spark records | `sparks-files` | [spark-records.md](spark-records.md) |
| Secrets and privacy | `secrets` | [secrets-and-privacy.md](secrets-and-privacy.md) |
| Links and formatting | `links`, `format` | [links-and-formatting.md](links-and-formatting.md) |

## Proof and skip reporting

- Report each check id with its status and every `FAIL`/`WARN` line, verbatim.
- `SKIP` means the input does not exist yet (`.gitignore`, `sparks/development-main`). Report it as skipped, not as passed or failed.
- Vendored findings (marked `(vendored, copied unchanged)`) are reported, never fixed in place.

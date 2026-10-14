# Tracked files and .gitignore

A clone should contain only source: no caches, OS metadata, editor leftovers, or local-only files. `.claude/` is tracked on purpose and is exempt.

## Sub-features

- `stray-tracked`: no tracked file matches the stray patterns in `STRAY_PATTERNS` (`__pycache__/`, `*.pyc`, `.DS_Store`, `*.local`, `.env*`, `*.swp`, `*~`, `*.tmp`, `*.log`, `node_modules/`, `.venv/`, and more).
- `large-or-symlink`: files over 1 MB and symlinks are `WARN`.
- `gitignore-coverage` (only when `.gitignore` exists): probes for Python caches, `.DS_Store`, `*.local`, swap and backup files, and `.env`. Each gap is `WARN`.
- `gitignore-keeps-claude`: `.gitignore` must not ignore `.claude/` (`FAIL`).
- `tracked-but-ignored`: tracked files that an ignore rule matches are `WARN`.

## How to get to it (user POV)

- `git clone` and browse the tree on GitHub.

## Driving it with check-sparks-hygiene

- `check-sparks-hygiene run --only tracked,gitignore`.
- With no `.gitignore`, `gitignore` shows `SKIP .gitignore not yet present`.
- Negative proof: in a throwaway clone, `git add -f` a `docs/__pycache__/a.pyc` and commit. `tracked` reports `FAIL docs/__pycache__/a.pyc is tracked (matches __pycache__/*)`. Append `.claude/` to that clone's `.gitignore` and commit. `gitignore` reports `FAIL ignores .claude/... must stay tracked`.

## Gotchas

- `.gitignore` contents are on hold pending an owner decision. Report coverage gaps. Do not edit the file.
- If `.gitignore` ignores `sparks.json`, the report notes it, because files tracked on `sparks/development-main` then need `git add -f`.

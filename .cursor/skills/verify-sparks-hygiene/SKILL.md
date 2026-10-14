---
name: verify-sparks-hygiene
description: "Verify that the gdsrvnt/sparks repository is clean and presentable as a public Cursor plugin: license and third-party notices agree, .cursor-plugin/plugin.json parses and its paths exist, no stray/cache/local-only files are tracked, no secrets or private text, relative markdown links resolve, formatting is consistent, and spark record files sit on the right branch and match spark.schema.json. Read-only; scripted with scripts/check-sparks-hygiene. Use before opening or merging a pull request, before a release or marketplace submission, or when asked whether the repo is clean."
disable-model-invocation: true
---

# Verify sparks hygiene

The surface checked here is the repository as a reader or the Cursor marketplace sees it: tracked files on the branch you are on. The plugin itself (`bin/sparks`, the skills) is not exercised. That needs its own drive. Everything is one read-only Python script (stdlib only) that reads tracked files from the working tree and git objects, and writes a report outside the checkout.

Hard rules:

- Never edit the checkout while verifying. The script does not write into it, and refuses an evidence directory inside it.
- `.claude/` is tracked on purpose (project-local agent skills). Do not flag it, untrack it, or propose ignoring it. The script exempts it from the stray-file check and fails if a `.gitignore` would ignore it.
- Do not create or edit `.gitignore`, and do not create the `sparks/development-main` branch. Both wait on owner decisions. The checks that use them run only when they exist.
- Report findings. Fix only what the task asks for. Files listed in `THIRD_PARTY_NOTICES.md` as copied unchanged are vendored: their findings are `WARN`, because fixing them in place breaks the "unchanged" promise.

All commands run from the repository root:

```bash
export PATH="$PWD/.cursor/skills/verify-sparks-hygiene/scripts:$PATH"
```

## 1. Launch

There is no server. Nothing to start. Needs `git` and `python3` >= 3.9. `jsonschema` is optional: when it is missing, spark records are checked against the rules read from `spark.schema.json` (array of objects with exactly `type`/`question`/`answer`, string values, `type` in the enum). To check the remote development branch, refresh refs first. The script never fetches:

```bash
git fetch origin
```

## 2. Doctor

```bash
check-sparks-hygiene doctor
```

Last line is `doctor: OK` or `doctor: FAIL`. It checks the Python version, that the repo is a git checkout with `origin` pointing at `gdsrvnt/sparks`, and that the manifest exists. It notes a dirty tree, because checks read working-tree content, so uncommitted edits count. For a verdict on a commit, run on a clean tree.

## 3. Drive

```bash
check-sparks-hygiene list                       # check ids
check-sparks-hygiene run                        # all checks
check-sparks-hygiene run --only links,format    # a subset
check-sparks-hygiene run --repo /path/to/other/checkout
check-sparks-hygiene run --deny-file ~/private-terms.txt   # or SPARKS_HYGIENE_DENYLIST=...
```

| Check | What it proves | Feature file |
| --- | --- | --- |
| `docs` | `README.md`, `LICENSE`, `THIRD_PARTY_NOTICES.md` tracked and non-empty; the LICENSE kind and holder match `plugin.json` `license`/`author` and the README `## License` section, which points to both files | [licensing-and-notices](features/licensing-and-notices.md) |
| `notices` | every path in the notices exists; every `skills/LICENSE-*` is referenced; every shipped skill is named in README; every skill in `.github/upstreams.json` exists and has a notice with the same pinned commit (missing notice = `WARN`) | [licensing-and-notices](features/licensing-and-notices.md) |
| `manifest` | `.cursor-plugin/plugin.json` parses; kebab-case `name`, semver `version`, https URLs; path fields (`logo`, `skills`, `rules`, `agents`, `commands`, `hooks`, `mcpServers`) exist inside the repo; with default discovery, every `skills/*/SKILL.md` has frontmatter whose `name` matches its directory, plus a `description` | [plugin-manifest](features/plugin-manifest.md) |
| `tracked` | no tracked `__pycache__`, `*.pyc`, `.DS_Store`, `*.local`, `.env*`, swap/backup files, logs, build or venv dirs (outside `.claude/`); large files and symlinks are `WARN` | [tracked-files-and-gitignore](features/tracked-files-and-gitignore.md) |
| `gitignore` | if a `.gitignore` exists: it covers cache/temp/local-only probes (`WARN` per gap) and does not ignore `.claude/` (`FAIL`); tracked-but-ignored files are `WARN`. Absent: `SKIP (not yet present)` | [tracked-files-and-gitignore](features/tracked-files-and-gitignore.md) |
| `sparks-files` | root `spark.json` matches `spark.schema.json`; off `sparks/development-main`, any other tracked `spark.json`/`sparks.json` is `FAIL`; if `sparks/development-main` or `origin/sparks/development-main` exists, every `sparks.json` on it is validated through `git show` (no checkout). Branch absent: `SKIP` | [spark-records](features/spark-records.md) |
| `secrets` | no token or key patterns, private key blocks, emails other than noreply/`example.*`, absolute home paths (`/home/<u>`, `/Users/<u>`, the root home directory, `C:\Users\<u>`), or denylisted terms in any tracked text file. Emails are masked in output and denylist hits show only the term's index | [secrets-and-privacy](features/secrets-and-privacy.md) |
| `links` | every relative link and reference definition in tracked markdown (outside code) resolves to a tracked file; missing `#anchors` are `WARN` | [links-and-formatting](features/links-and-formatting.md) |
| `format` | text files end with exactly one newline, no CRLF, no trailing whitespace; `*.json` parses; files with a shebang are mode `100755` in git | [links-and-formatting](features/links-and-formatting.md) |

Statuses: `PASS`, `FAIL`, `WARN` (reported, not failing), `SKIP` (input not present yet). Exit `0` with no `FAIL`, `1` with any `FAIL`, `2` on usage errors. The last report line is `summary: N pass, N fail, N warn, N skip -> PASS|FAIL`.

The private-term denylist lives outside the repo (one term per line, `#` comments). Never commit it. Without one, the script still runs every pattern check.

## 4. Evidence

`run` prints the report and saves it as `report.txt` and `report.json` in `$VERIFY_SPARKS_HYGIENE_EVIDENCE/<stamp>-<head>/` (default `~/.local/state/verify-sparks-hygiene/`), or in `--out DIR`. The last line of output is `evidence: <dir>`. A proof quotes the summary line, every `FAIL`/`WARN` line, the HEAD it ran on, and whether the tree was clean (from `doctor`). To prove a check catches what it claims, plant the problem in a throwaway clone (`git clone -q . "$tmp"`), commit it there, and run `check-sparks-hygiene run --repo "$tmp"`. Never plant it in the real checkout.

## 5. Cleanup

Nothing is started, so nothing needs killing. Delete only throwaway clones you made for negative tests. Keep the evidence directories. They are the proof.

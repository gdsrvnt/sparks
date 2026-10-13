# Entry add

Entry add is how a person or an agent writes one spark record. The command creates a missing file, refuses a bad record without writing, and replaces a record whose question matches exactly, keeping the id already stored.

## Sub-features

- `add-create` creates a missing file and prints `added <id>`.
- `add-refuse` rejects invalid JSON with one stderr line and does not write.
- `add-replace` replaces by exact question and keeps the stored id.

## How to get to it (user POV)

- Run `bin/sparks entry add --json '<record>'` in a project directory. The file is `./sparks.json`.
- Run `bin/sparks entry add --path <path> --json '<record>'` to name the file.
- On Windows, run `uv run --script bin/sparks entry add ...`.

## Driving it with check-verify-sparks

Preconditions:

- `check-verify-sparks doctor` ended with `doctor: OK`.
- No drive uses the checkout's `spark.json` or a `sparks.json` the user already has.

- **Create, explicit path.** Run `check-verify-sparks entry-add`. The helper uses `uv run --script bin/sparks entry add --path <scratch>/named.json`. Exit `0` for this command means this drive passed. `entry-add.txt` records argv, cwd, exit, and both streams. The written file is also copied to `entry-add-file.json` before scratch is deleted.
- **Refuse.** The same command sends `{` as `--json`. The drive passes only if that refusal exited `1`, stderr starts with `sparks: `, stderr is one line, and the file bytes did not change.
- **Replace.** The same command then adds the same question with a different answer. The file has one record. Its `id` is the id from the create.
- **Default path.** The same command also runs `entry add --json` with no `--path`, cwd set to a scratch directory. It must create `./sparks.json` there. This is the default-path entry. It is not the user's existing `sparks.json`.
- **Not exercised.** A shell that invokes `bin/sparks` by its shebang, without `uv run --script`, is not this drive. On Windows the user form is `uv run --script`, which is the form the helper uses.
- **Proof.** Quote `entry-add.txt` and the `entry-add` row. The scratch directory is gone after the command returns. This command's exit code does not clear an earlier `FAIL` in a merged report.

## Gotchas

- The success line says `added` for a replacement too. The proof is the file, not the verb.
- A record passed on the command line has no `id`. The helper does not send one.
- Matching is the decoded question, not the hash. A different answer under the same question is a replacement.
- Do not point this drive at `~/.local/share` or the repo root. The helper picks the temp directory.

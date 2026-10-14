# Add

`sparks add` is how a person or an agent writes one spark. The command creates a missing file, refuses a bad spark without writing, and replaces a spark whose question matches exactly, keeping the id already stored.

## Sub-features

- `add-create` creates a missing file and prints `added <id> to <path>`.
- `add-refuse` rejects invalid JSON with one stderr line and does not write.
- `add-replace` replaces by exact question and keeps the stored id.

## How to get to it (user POV)

- Run `bin/sparks add --json '<spark>'` in a project directory. `--path` defaults to `./sparks.json`.
- Run `bin/sparks add --path <path> --json '<spark>'` to name the file.
- On Windows, run `uv run --script bin/sparks add ...`.

There is no `entry add` command and no `spark add` command. `bin/spark` is an unrelated placeholder.

## Driving it with check-verify-sparks

Preconditions:

- `check-verify-sparks doctor` ended with `doctor: OK`.
- No drive uses the checkout's `sparks.json` or a `sparks.json` the user already has.

- **Create, explicit path.** Run `check-verify-sparks add`. The helper uses `uv run --script bin/sparks add --path <scratch>/named.json`. Exit `0` for this command means this drive passed. `add.txt` records argv, cwd, exit, and both streams. The written file is also copied to `add-file.json` before scratch is deleted.
- **Refuse.** The same command sends `{` as `--json`. The drive passes only if that refusal exited `1`, stderr starts with `sparks: `, stderr is one line, and the file bytes did not change.
- **Replace.** The same command then adds the same question with a different answer. The file has one spark. Its `id` is the id from the create. The written `type` is lowercase `s`.
- **Default path.** The same command also runs `sparks add --json` with no `--path`, cwd set to a scratch directory. It must create `./sparks.json` there. This is the default path. It is not the user's existing `sparks.json`.
- **Not exercised.** A shell that invokes `bin/sparks` by its shebang, without `uv run --script`, is not this drive. On Windows the user form is `uv run --script`, which is the form the helper uses.
- **Proof.** Quote `add.txt` and the `add` row. The scratch directory is gone after the command returns. This command's exit code does not clear an earlier `FAIL` in a merged report.

## Gotchas

- The success line says `added <id> to <path>` for a replacement too. The proof is the file, not the verb.
- A spark passed on the command line has no `id`. The helper does not send one. `parse_spark` refuses an `id` on input; `sparks add` assigns it.
- Matching is the decoded question, not the hash. A different answer under the same question is a replacement, and the stored id is kept.
- Do not point this drive at `~/.local/share` or the repo root. The helper picks the temp directory.

# Semantic contradiction

Semantic contradiction is the check that the sparks repository's current claims agree with each other and with the code. It is source-wide. A green pytest run does not satisfy it.

## Sub-features

- `claims-index` lists normative prose, implementation, and non-normative evidence. The prose pass reads the first two. The list is `index.txt`, not a second copy in this file.
- `type-set` compares the schema enum set with `spark_id.TYPES`. It does not parse English.
- `id-optional` checks the schema required set. It does not parse English.
- `skill-names` checks that each `skills/*/SKILL.md` frontmatter `name` matches its directory.
- `prose-pass` is the agent read. Type wording, hash name, post-call ownership, and changelog claims are decided here, not by the script.

## How to get to it (user POV)

- Open the sparks checkout and run the verification skill before opening a pull request.
- Ask an agent to verify the repository, not a single diff.
- There is no browser and no separate app to launch.

## Driving it with check-verify-sparks

Preconditions:

- `check-verify-sparks doctor` ended with `doctor: OK`.
- Evidence will be written outside the checkout.

- **Index and decidable claims.** Run `check-verify-sparks contradict`. Exit `0` or `1`. Stdout contains a `summary:` line, a `script-pass is not a verification pass` line, and an `evidence:` line. `index.txt` in that directory is the file list. A `FAIL` row is a structural mismatch, not a prose grade.
- **Prose pass.** Read every path under `# normative` and `# implementation` in `index.txt`, from the checkout the doctor printed. Skip `# evidence-not-normative`. For each file, write either `none` or a contradiction. A contradiction quotes both sides and names both paths. Current means the normative files plus the implementation they describe. `CHANGELOG.md` under a version heading is history; `## [Unreleased]` is current. `docs/vision-transcript.md` is a call transcript, not a current contract. Vendored skill bodies are not indexed. Answer these in `prose.md`; a substring match is not an answer:
  - Do `rules/post-call-self-healing.mdc`, `skills/spark-voice/SKILL.md` hang-up, and `skills/sparks-postcall/SKILL.md` agree that hang-up does no post-call work and that the protocol lives only in `sparks-postcall`?
  - Does `skills/spark-verification/SKILL.md` stay read-only (no edits, no pull requests, no create/maintain modes), and does README say the same?
  - Does `rules/blocker-clearing.mdc` still offer a stop-and-deliberate path that runs `sparks-discuss` and records the outcome as a spark?
  - Do Unreleased changelog claims about type case, id optionality, the hash, and skill names match the schema, README, and the skills? Type letters in `sparks.json` are lowercase `s`, `p`, `a`, `r`, `k`. The command is `sparks add [--path]`; there is no `entry add` or `spark add`. The files are `sparks.json` and `sparks.schema.json`, not `spark.json` or `spark.schema.json`. A typed Q&A item is a spark; a `sparks.json` is a list of sparks.
  - Does `docs/duplicate-detection.md` still say fuzzy flagging is not implemented, in agreement with `bin/sparks`?
- **Write the proof.** Save that read as `prose.md` in the evidence directory from the `evidence:` line. One heading per normative and implementation path. The drive is incomplete if any of those paths is missing from `prose.md`.
- **Do not fix.** Leave the checkout unchanged. A `FAIL` is the result, not a cue to edit the file under test.

## Gotchas

- `spark-verification` checks a diff against `sparks.json`. This feature checks this repo's sources against each other. Passing one does not pass the other.
- `## [Unreleased]` is current even when an older bullet was superseded by a later commit. If two Unreleased bullets disagree, that is a contradiction.
- The script does not read type lists out of sentences. A lowercase schema and an Unreleased bullet that requires uppercase types is a prose contradiction even when `contradict` exits `0`.
- Vendored skills may disagree with sparks. That is not a sparks contradiction unless README or another first-party file states their internals as sparks' own rule.
- Do not treat a missing `prose.md` as a pass because `contradict` exited `0`.

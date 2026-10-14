# Format

A spark is the primitive: one typed question-and-answer pair, with an optional `id` that `sparks add` writes on insertion.

spark is for a person or an agent who keeps context in a list of sparks next to the code. Each spark is one question and one answer. The type is one lowercase letter: s, p, a, r, or k. `bin/sparks` accepts any case and writes lowercase. `spark_id.py` hashes the spark with XXH64. The input is one JSON object. That object holds the answer, the question, and the type, with keys in alphabetical order and no extra whitespace. Use spark when the question and the answer identify the spark, and the file may move between directories.

The repository is named sparks. The format is named spark.

`sparks.json` is a list of sparks, represented as a JSON array. The repository root `sparks.json` is an example of that list. Each spark is an object with three required keys and an optional `id`. Files without ids stay valid.

| Key | Rule |
| --- | --- |
| `type` | One of `s`, `p`, `a`, `r`, `k` (lowercase) |
| `question` | A string |
| `answer` | A string |
| `id` | Optional. 16 lowercase hex characters, written by `sparks add` |

`spark_id.py` hashes `question`, `answer`, and `type`. It writes one JSON object with the keys `answer`, `question`, and `type`, in alphabetical order, with no extra whitespace. The bytes are UTF-8. `spark_id.py` does not trim strings, and it does not apply Unicode normalization. The derived id is XXH64 with seed 0 over those bytes, as 16 lowercase hex characters. The hash lives in `spark_hash.py`, a pure Python standard-library implementation with zero dependencies, checked against reference test vectors. XXH64 is fast, has a published specification, and gives 64 bits, so collisions stay unlikely well past millions of sparks. A stored `id` is the spark's reference: `load` checks its shape but does not recompute it, so hand edits do not break it. A spark without `id` uses its derived id.

The same question, answer, and type derive the same id on every machine. `connect` in `spark_id.py` unions sparks that `load` already returned. It does not walk a directory. The same id with a different question, answer, or type is an error.

`sparks.schema.json` checks the array shape. `spark_id.py` derives ids for sparks without one, checks stored id shape (without rehashing), and refuses duplicate ids. The schema `$id` is `https://raw.githubusercontent.com/gdsrvnt/sparks/main/sparks.schema.json`.

`bin/spark` is a placeholder. It has no features.

`bin/sparks add` adds one spark or replaces the entire spark with an exactly equal decoded `question` string in the target list, regardless of type. `--path` defaults to `./sparks.json` in the working directory. Replacement keeps its array position; no match appends. Matching does not normalize whitespace, case, punctuation, or Unicode. Multiple exact matches are refused without writing; an identical spark that already has its stored id succeeds without rewriting; one without an id is rewritten once to add it. The content hash is not the replacement key. It checks the spark and the list with `sparks.schema.json` and `spark_id.py`. It writes the `id` as the spark's last key. A `--json` spark may not carry an `id`. A replacement keeps the id the spark already stored; a spark without one gets one. The README shows how to use it.

# Format

Question and answer records, each with a content id that `bin/sparks` assigns when the record is added.

Spark is for a person or an agent who keeps context in a file next to the code. Each record is one question and one answer. The type is one letter: S, P, A, R, or K. Each record also stores an `id`, a hash of the record. That hash is XXH3-64 of one JSON object. That object holds the answer, the question, and the type, with keys in alphabetical order and no extra whitespace. Use Spark when the question and the answer identify the note, and the file may move between directories.

The repository is named sparks. The format is named Spark.

`spark.json` is a JSON array. Each object has four keys.

| Key | Rule |
| --- | --- |
| `type` | One of `S`, `P`, `A`, `R`, `K` |
| `question` | A string |
| `answer` | A string |
| `id` | 16 lowercase hexadecimal characters, the XXH3-64 content id |

`spark_id.py` hashes `question`, `answer`, and `type`. It writes one JSON object with the keys `answer`, `question`, and `type`, in alphabetical order, with no extra whitespace. The bytes are UTF-8. `spark_id.py` does not trim strings, and it does not apply Unicode normalization. The `id` is the XXH3-64 (xxHash, seed 0) digest of those bytes, as 16 lowercase hexadecimal characters. The file stores that id, and `load` refuses a file whose stored id does not match its record. The stored id is not hashed.

The hash is not cryptographic, and it does not need to be: nothing here defends against someone who forges a collision on purpose. XXH3-64 is fast and specified, with ports in most languages. It has 64 bits, so an accidental collision is negligible at any realistic file size. A 32-bit hash such as fasthash32 is not: the birthday bound gives about a 1% chance of a collision by roughly 9,300 records.

The same question and answer produce the same id on every machine. `connect` in `spark_id.py` unions records that `load` already returned. It does not walk a directory. The same id with a different question or answer is an error.

`spark.schema.json` checks the array shape. The hash check stays in `spark_id.py`. The schema `$id` is `https://raw.githubusercontent.com/gdsrvnt/sparks/main/spark.schema.json`.

`bin/spark` is a placeholder. It has no features.

`bin/sparks entry add` adds one record or replaces the entire record with an exactly equal decoded `question` string in the target file, regardless of type. Replacement keeps its array position; no match appends. Matching does not normalize whitespace, case, punctuation, or Unicode. Multiple exact matches are refused without writing; an identical record succeeds without rewriting. The content hash is not the replacement key. It assigns the `id` on ingress: the `--json` record has no `id` key, and the command refuses one. It checks the record and the file with `spark.schema.json` and `spark_id.py`, then writes the record with its `id`. A replacement gets a new `id`, because the id follows the content. Its default file is `sparks.json`, the name the README uses; `spark.json` in this repository is an example. The README shows how to use it.

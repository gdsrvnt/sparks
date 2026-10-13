# Format

Question and answer records. An id can be recomputed, but the file does not store it.

Spark is for a person or an agent who keeps context in a file next to the code. Each record is one question and one answer. The type is one letter: S, P, A, R, or K. `spark_id.py` can still hash the record. That hash is the last 16 characters of a SHA-256 of one JSON object. That object holds the answer, the question, and the type, with keys in alphabetical order and no extra whitespace. Use Spark when the question and the answer identify the note, and the file may move between directories.

The repository is named sparks. The format is named Spark.

`spark.json` is a JSON array. Each object has three keys. There is no `id` key.

| Key | Rule |
| --- | --- |
| `type` | One of `S`, `P`, `A`, `R`, `K` |
| `question` | A string |
| `answer` | A string |

`spark_id.py` hashes `question`, `answer`, and `type`. It writes one JSON object with the keys `answer`, `question`, and `type`, in alphabetical order, with no extra whitespace. The bytes are UTF-8. `spark_id.py` does not trim strings, and it does not apply Unicode normalization. The `id` is the last 16 characters of the SHA-256 hexadecimal digest. The file does not store that id.

The same question and answer produce the same id on every machine. `connect` in `spark_id.py` unions records that `load` already returned. It does not walk a directory. The same id with a different question or answer is an error.

`spark.schema.json` checks the array shape. The hash check stays in `spark_id.py`. The schema `$id` is `https://raw.githubusercontent.com/gdsrvnt/sparks/main/spark.schema.json`.

`bin/spark` is a placeholder. It has no features.

`bin/sparks entry add` appends one record to a file. It checks the record and the file with `spark.schema.json` and `spark_id.py`. It does not write an `id`. Its default file is `sparks.json`, the name the README uses; `spark.json` in this repository is an example. The README shows how to use it.

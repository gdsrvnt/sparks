# Id and hash

The id of a spark is XXH64 (seed 0) of the canonical preimage, written as 16 lowercase hex characters. The example `sparks.json` stores that id. A stored id is the spark's reference; `spark_id.load` checks its shape and does not recompute it.

## Sub-features

- `vectors` checks `spark_hash.py` against the published XXH64 sanity-check rows.
- `example-id` checks that every stored id in `sparks.json` equals `derive_id` of that spark's question, answer, and type.
- `load-shape` checks that `spark_id.py` accepts the example file.

## How to get to it (user POV)

- Read the id `sparks add` prints (`added <id> to <path>`).
- Open `sparks.json` in the repo and compare its `id` to the spark text.
- Run `uv run spark_id.py sparks.json` and expect silence and exit `0`.

## Driving it with check-verify-sparks

Preconditions:

- `check-verify-sparks doctor` ended with `doctor: OK`.
- `sparks.json` is the committed example, not a scratch file.

- **Vectors.** Run `check-verify-sparks contradict`. The `vectors` row is `PASS` only if every official row matches this checkout's `spark_hash.py`. `--repo` loads that checkout's module, not the helper's. A mismatch prints `len`, `seed`, and both digests.
- **Example id.** The same command's `example` row is `PASS` only if every `id` in `sparks.json` equals `derive_id` of its question, answer, and lowercase type, and `uv run spark_id.py sparks.json` exits `0`. The transcript is `spark-id.txt`.
- **Not exercised.** `python3 spark_hash.py` on stdin is a user path. This drive does not run it. The published vectors call `spark_hash.xxh64_hexdigest` in process.
- **Proof.** Quote the `vectors` and `example` rows from `report.txt`. Do not treat a matching `spark_id.load` as proof of the hash: load does not recompute a stored id.

## Gotchas

- `derive_id` and a stored id are different questions. A hand-edited id can still load. The example check is the one that compares them.
- The official rows use the xxHash sanity-check buffer, not the UTF-8 of the length number. A generator that fills the wrong bytes can fake a table; the helper locks the 16-byte prefix `0052929bb732a3242d00af950eecb893`.
- XXH3 and SHA-256 are not the current hash. A current claim that names them is a prose contradiction, not a `vectors` failure. The type letters in `sparks.json` are lowercase `s`, `p`, `a`, `r`, `k`; `derive_id` hashes the type string as stored.

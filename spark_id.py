# /// script
# requires-python = ">=3.11"
# dependencies = ["xxhash>=3.4"]
# ///

"""``_preimage`` is the normative serializer. The id is the 16 lowercase hex
characters of XXH3-64 (seed 0) over the UTF-8 of that JSON object. Files store
the id; the stored id is not an input. Strings are not trimmed and not
Unicode-normalized. The hash is not cryptographic and does not need to be.
"""

import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import xxhash

_ID_RE = re.compile(r"^[0-9a-f]{16}$")
TYPES = ("S", "P", "A", "R", "K")


class SparkFileError(Exception):
    """A file or a connect input broke the format or the id rule."""


def _preimage(question: str, answer: str, spark_type: str) -> bytes:
    return json.dumps(
        {"answer": answer, "question": question, "type": spark_type},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


@dataclass(frozen=True)
class Spark:
    """One immutable SPARK record. Its id is derived from its exact strings."""

    question: str
    answer: str
    type: str = "S"
    id: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.question, str) or not isinstance(self.answer, str):
            raise TypeError("question and answer must be str")
        if self.type not in TYPES:
            raise SparkFileError("type must be one of S, P, A, R, K")
        try:
            digest = xxhash.xxh3_64_hexdigest(
                _preimage(self.question, self.answer, self.type)
            )
        except UnicodeEncodeError as exc:
            raise SparkFileError("preimage is not UTF-8") from exc
        object.__setattr__(self, "id", digest)


def load(path: Path) -> tuple[Spark, ...]:
    """Read one spark.json file into Sparks, in array order.

    Does not search parent or child directories and does not write.
    An empty array returns (). JSON errors, OS errors, shape errors, a
    stored id that does not match its record, and SparkFileError from
    Spark construction raise SparkFileError.
    Does not return a partial tuple.
    """
    if not isinstance(path, Path):
        raise TypeError("path must be pathlib.Path")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SparkFileError(exc.strerror or "cannot read file") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SparkFileError("file is not UTF-8") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SparkFileError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(data, list):
        raise SparkFileError("expected a JSON array")
    found: list[Spark] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, dict) or set(item) != {"type", "question", "answer", "id"}:
            raise SparkFileError(
                "each record must be an object with keys type, question, answer, and id"
            )
        wire_type = item["type"]
        question = item["question"]
        answer = item["answer"]
        stored = item["id"]
        if (
            wire_type not in TYPES
            or not isinstance(question, str)
            or not isinstance(answer, str)
            or not isinstance(stored, str)
            or _ID_RE.fullmatch(stored) is None
        ):
            raise SparkFileError(
                "type must be one of S, P, A, R, K, question and answer must be strings, "
                "and id must be 16 lowercase hex characters"
            )
        built = Spark(question, answer, wire_type)
        if built.id != stored:
            raise SparkFileError("stored id does not match the record")
        if built.id in seen:
            raise SparkFileError("duplicate id")
        seen.add(built.id)
        found.append(built)
    return tuple(found)


def connect(*groups: Iterable[Spark]) -> tuple[Spark, ...]:
    """Set-union by id of Sparks that are already loaded.

    Walks groups in argument order, then each Spark in iteration order.
    The first Spark for an id is kept. A later Spark with that id and the
    same question and answer is skipped. A later Spark with that id and a
    different question or answer raises SparkFileError. Does not return a
    partial tuple. A non-Spark raises TypeError.

    Does not read the filesystem and does not rehash.
    connect(connect(a, b), a) == connect(a, b) when a and b do not conflict.
    """
    first: dict[str, Spark] = {}
    ordered: list[Spark] = []
    for group in groups:
        for spark in group:
            if not isinstance(spark, Spark):
                raise TypeError("connect expects Spark values")
            kept = first.get(spark.id)
            if kept is None:
                first[spark.id] = spark
                ordered.append(spark)
                continue
            if kept.question != spark.question or kept.answer != spark.answer:
                raise SparkFileError("same id with a different question or answer")
    return tuple(ordered)


def main(argv: list[str]) -> int:
    """Check one file with load. No flags and no subcommands.

    argv must be the program and one path. Otherwise write the usage line
    to stderr and return 1. On success write nothing and return 0. On
    SparkFileError write ``spark_id: <path>: <message>`` and return 1.
    """
    if len(argv) != 2:
        sys.stderr.write("spark_id: usage: uv run spark_id.py <spark.json>\n")
        return 1
    path = argv[1]
    try:
        load(Path(path))
    except SparkFileError as exc:
        sys.stderr.write(f"spark_id: {path}: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""``_preimage`` is the normative serializer. The derived id is XXH64 (seed 0)
of the UTF-8 of that JSON object, as 16 lowercase hex characters, computed by
the bundled, dependency-free ``spark_hash.py``. A spark may store that id
under the optional ``id`` key; ``sparks spark add`` writes it on insertion.
A stored id is kept as the spark's reference and is not recomputed, so a
file without ids stays valid and a stored id survives later hand edits.
Strings are not trimmed and not Unicode-normalized.
"""

import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from spark_hash import xxh64_hexdigest  # noqa: E402

TYPES = ("s", "p", "a", "r", "k")
ID_PATTERN = re.compile(r"[0-9a-f]{16}")


class SparkFileError(Exception):
    """A file or a connect input broke the format or the id rule."""


def derive_id(question: str, answer: str, spark_type: str) -> str:
    """XXH64 (seed 0) of the preimage, as 16 lowercase hex characters."""
    try:
        return xxh64_hexdigest(_preimage(question, answer, spark_type))
    except UnicodeEncodeError as exc:
        raise SparkFileError("preimage is not UTF-8") from exc


def _preimage(question: str, answer: str, spark_type: str) -> bytes:
    return json.dumps(
        {"answer": answer, "question": question, "type": spark_type},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


@dataclass(frozen=True)
class Spark:
    """One immutable spark. Its id is the stored id, else derived from its strings."""

    question: str
    answer: str
    type: str = "s"
    id: str | None = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.question, str) or not isinstance(self.answer, str):
            raise TypeError("question and answer must be str")
        if isinstance(self.type, str):  # any case is accepted; the canonical type is lowercase
            object.__setattr__(self, "type", self.type.lower())
        if self.type not in TYPES:
            raise SparkFileError("type must be one of s, p, a, r, k (any case)")
        if self.id is None:
            object.__setattr__(self, "id", derive_id(self.question, self.answer, self.type))
            return
        if not isinstance(self.id, str) or not ID_PATTERN.fullmatch(self.id):
            raise SparkFileError("id must be 16 lowercase hex characters")
        try:  # a stored id is not rehashed, but the strings must still be UTF-8
            _preimage(self.question, self.answer, self.type)
        except UnicodeEncodeError as exc:
            raise SparkFileError("preimage is not UTF-8") from exc


def load(path: Path) -> tuple[Spark, ...]:
    """Read a list of sparks from one JSON file, in array order.

    Does not search parent or child directories and does not write.
    An empty array returns (). JSON errors, OS errors, shape errors,
    and SparkFileError from Spark construction raise SparkFileError.
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
        if not isinstance(item, dict) or not (
            {"type", "question", "answer"} <= set(item) <= {"type", "question", "answer", "id"}
        ):
            raise SparkFileError(
                "each spark must be an object with keys type, question, and answer, "
                "and optionally id"
            )
        wire_type = item["type"]
        question = item["question"]
        answer = item["answer"]
        if (
            not isinstance(wire_type, str)
            or wire_type.lower() not in TYPES
            or not isinstance(question, str)
            or not isinstance(answer, str)
        ):
            raise SparkFileError(
                "type must be one of s, p, a, r, k (any case), and question and answer must be strings"
            )
        if "id" in item and not isinstance(item["id"], str):
            raise SparkFileError("id must be 16 lowercase hex characters")
        built = Spark(question, answer, wire_type, item.get("id"))
        if built.id in seen:
            raise SparkFileError("duplicate id")
        seen.add(built.id)
        found.append(built)
    return tuple(found)


def connect(*groups: Iterable[Spark]) -> tuple[Spark, ...]:
    """Set-union by id of Sparks that are already loaded.

    Walks groups in argument order, then each Spark in iteration order.
    The first Spark for an id is kept. A later Spark with that id and the
    same question, answer, and type is skipped. A later Spark with that id and
    a different question, answer, or type raises SparkFileError. Does not return a
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
            if (kept.question, kept.answer, kept.type) != (
                spark.question, spark.answer, spark.type
            ):
                raise SparkFileError("same id with a different question, answer, or type")
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

# /// script
# requires-python = ">=3.11"
# dependencies = ["jsonschema>=4.18", "pytest>=8"]
# ///

"""Tests for bin/sparks. Run them with ``uv run tests/test_sparks.py``."""

import contextlib
import copy
import errno
import importlib.machinery
import importlib.util
import io
import json
import os
import re
import shutil
import signal
import sqlite3
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "sparks"
sys.path.insert(0, str(ROOT))

import spark_hash  # noqa: E402
import spark_id as spark_id_mod  # noqa: E402

posix = pytest.mark.skipif(os.name != "posix", reason="needs POSIX modes, signals, or flock")


def _import_cli():
    """bin/sparks has no .py suffix, so in-process tests load it by path."""
    loader = importlib.machinery.SourceFileLoader("sparks_cli", str(BIN))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    return module


cli = _import_cli()


def spark(question="Why is main protected?", answer="Every merge must pass CI first.", spark_type="s"):
    return {
        "type": spark_type,
        "question": question,
        "answer": answer,
    }


def spark_id(spark):
    return spark_id_mod.Spark(spark["question"], spark["answer"], spark["type"]).id


def stored(spark):
    """A spark the way sparks add writes it: with its id as the last key."""
    return {**spark, "id": spark_id(spark)}


FIRST = spark()
SECOND = spark("Who reviews skill changes?", "Anyone who did not write them.")


def sparks(*args, cwd, env=None, **kwargs):
    """Run bin/sparks in a child process, the way a shell would.

    env only adds variables. The full environment stays a local, so a failing
    test's traceback does not print it.
    """
    environment = {**os.environ, "COLUMNS": "80", **(env or {})}  # COLUMNS: help wrapping
    return subprocess.run(
        [sys.executable, str(BIN), *args],
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        env=environment,
        **kwargs,
    )


def add(path, spark, *, cwd=None, **kwargs):
    text = spark if isinstance(spark, str) else json.dumps(spark)
    return sparks(
        "add", "--path", str(path), "--json", text, cwd=cwd or path.parent, **kwargs
    )


def command(path, spark):
    """The argv of a bin/sparks run that adds one spark to path."""
    args = ["add", "--path", str(path), "--json", json.dumps(spark)]
    return [sys.executable, str(BIN), *args]


def run_main(path, spark):
    """In-process run, so tests can break os functions halfway through a write."""
    return cli.main(["add", "--path", str(path), "--json", json.dumps(spark)])


def seed(path, sparks):
    """Write a list of sparks the way the CLI does and return its bytes."""
    path.write_bytes((json.dumps(sparks, ensure_ascii=False, indent=2) + "\n").encode())
    return path.read_bytes()


def others(directory, name="sparks.json"):
    """Everything in directory except the list of sparks: leftover temp or lock files."""
    return sorted(p.name for p in directory.iterdir() if p.name != name)


def assert_rejected(result, message, code=1):
    assert result.returncode == code
    assert result.stdout == ""
    assert result.stderr.startswith("sparks: "), result.stderr
    assert result.stderr.count("\n") == 1, result.stderr  # one line, no traceback
    assert message in result.stderr


# create, append, default path


def test_creates_a_missing_file_with_the_spark(tmp_path):
    path = tmp_path / "sparks.json"
    result = add(path, FIRST)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"added {spark_id(FIRST)} to {path}\n"
    assert result.stderr == ""
    assert json.loads(path.read_bytes()) == [stored(FIRST)]
    assert others(tmp_path) == []


def test_output_matches_the_repo_example_byte_for_byte(tmp_path):
    example = ROOT / "sparks.json"
    path = tmp_path / "sparks.json"
    for spark in json.loads(example.read_bytes()):
        del spark["id"]  # sparks assigns the id on add
        assert add(path, spark).returncode == 0
    # A Windows checkout may have turned the example's line endings into CRLF.
    assert path.read_bytes() == example.read_bytes().replace(b"\r\n", b"\n")


def test_default_path_is_sparks_json_in_the_working_directory(tmp_path):
    for spark in (FIRST, SECOND):  # creates, then appends
        result = sparks("add", "--json", json.dumps(spark), cwd=tmp_path)
        assert result.returncode == 0, result.stderr
        assert result.stdout == f"added {spark_id(spark)} to sparks.json\n"
    assert json.loads((tmp_path / "sparks.json").read_bytes()) == [stored(FIRST), stored(SECOND)]
    assert others(tmp_path) == []


def test_relative_path_resolves_against_the_working_directory(tmp_path):
    (tmp_path / "docs").mkdir()
    result = sparks(
        "add", "--path", "docs/notes.json", "--json", json.dumps(FIRST), cwd=tmp_path
    )
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / "docs" / "notes.json").read_bytes()) == [stored(FIRST)]


def test_appends_after_existing_sparks_and_keeps_them(tmp_path):
    path = tmp_path / "sparks.json"
    # Hand-written: compact, with keys in a different order.
    hand_written = {key: FIRST[key] for key in ("answer", "question", "type")}
    path.write_bytes(json.dumps([hand_written]).encode())
    third = spark("Is a third spark kept in order?", "Yes, at the end.")
    assert add(path, SECOND).returncode == 0
    assert add(path, third).returncode == 0
    sparks = json.loads(path.read_bytes())
    assert sparks == [FIRST, stored(SECOND), stored(third)]
    assert list(sparks[0]) == ["answer", "question", "type"]


def test_new_spark_is_stored_in_schema_key_order(tmp_path):
    path = tmp_path / "sparks.json"
    shuffled = json.dumps({key: FIRST[key] for key in ("answer", "question", "type")})
    assert add(path, shuffled).returncode == 0
    assert list(json.loads(path.read_bytes())[0]) == ["type", "question", "answer", "id"]


def test_non_ascii_is_kept_verbatim_and_hashed_by_the_spec_rule(tmp_path):
    question = "¿Por qué “verbatim”?"
    answer = "Naïve café prose — 日本語 🙂, kept as written."
    preimage = json.dumps(
        {"answer": answer, "question": question, "type": "s"},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    spark = {"type": "s", "question": question, "answer": answer}
    assert spark_id(spark) == spark_hash.xxh64_hexdigest(preimage.encode("utf-8"))
    path = tmp_path / "sparks.json"
    result = add(path, spark)
    assert result.returncode == 0, result.stderr
    text = path.read_bytes().decode("utf-8")
    assert question in text and answer in text  # no \u escapes
    assert json.loads(text) == [stored(spark)]



@pytest.mark.parametrize("spark_type", ["S", "s", "R", "k", "K"])
def test_type_is_accepted_in_any_case_and_written_lowercase(tmp_path, spark_type):
    path = tmp_path / "sparks.json"
    result = add(path, spark(spark_type=spark_type))
    assert result.returncode == 0, result.stderr
    assert json.loads(path.read_bytes()) == [stored(spark(spark_type=spark_type.lower()))]
    assert spark_id_mod.Spark("q", "a", spark_type).id == spark_id_mod.Spark("q", "a", spark_type.lower()).id


def test_legacy_uppercase_file_is_read_and_rewritten_lowercase(tmp_path):
    path = tmp_path / "sparks.json"
    path.write_text(json.dumps([spark(spark_type="P")]), encoding="utf-8")
    assert len(spark_id_mod.load(path)) == 1
    result = add(path, SECOND)
    assert result.returncode == 0, result.stderr
    assert json.loads(path.read_bytes()) == [spark(spark_type="p"), stored(SECOND)]

@pytest.mark.parametrize("spark_type", ["s", "r"])
def test_exact_question_replaces_whole_spark_in_place(tmp_path, spark_type):
    path = tmp_path / "sparks.json"
    third = spark("Another question?", "Another answer.")
    seed(path, [SECOND, FIRST, third])
    revised = spark(FIRST["question"], "Every merge must pass CI and one review.", spark_type)
    result = add(path, revised)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"added {spark_id(revised)} to {path}\n"
    assert json.loads(path.read_bytes()) == [SECOND, stored(revised), third]
    assert spark_id(revised) != spark_id(FIRST)
    assert others(tmp_path) == []


@pytest.mark.parametrize("question", [
    FIRST["question"].lower(), " " + FIRST["question"], FIRST["question"] + " ",
    FIRST["question"][:-1], "Why is main\nprotected?", "", "Café?", "Cafe\u0301?",
])
def test_non_exact_questions_append_without_normalization(tmp_path, question):
    path = tmp_path / "sparks.json"
    original = spark("Café?") if question == "Cafe\u0301?" else FIRST
    seed(path, [original])
    incoming = spark(question)
    assert add(path, incoming).returncode == 0
    assert json.loads(path.read_bytes()) == [original, stored(incoming)]


def test_json_escape_spelling_does_not_change_question_identity(tmp_path):
    path = tmp_path / "sparks.json"
    original = spark("Café?")
    seed(path, [original])
    revised = spark(original["question"], "Updated.")
    assert add(path, json.dumps(revised, ensure_ascii=True)).returncode == 0
    assert json.loads(path.read_bytes()) == [stored(revised)]


@pytest.mark.parametrize("incoming", [FIRST, spark(FIRST["question"], "Updated.")])
def test_multiple_exact_matches_are_refused_without_writing(tmp_path, incoming):
    path = tmp_path / "sparks.json"
    before = seed(path, [FIRST, SECOND, spark(FIRST["question"], "Old answer.", "r")])
    result = sparks("add", "--json", json.dumps(incoming), cwd=tmp_path)
    assert_rejected(result, "2 sparks have the exact question")
    assert path.read_bytes() == before
    assert others(tmp_path) == []


def test_failed_replacement_keeps_old_spark(tmp_path, monkeypatch, capsys):
    path = tmp_path / "sparks.json"
    before = seed(path, [FIRST, SECOND])

    def fail(src, dst):
        raise OSError(errno.EIO, "simulated replacement failure")

    monkeypatch.setattr(os, "replace", fail)
    assert run_main(path, spark(FIRST["question"], "Updated.")) == 1
    assert "cannot write" in capsys.readouterr().err
    assert path.read_bytes() == before
    assert others(tmp_path) == []


@posix
def test_concurrent_adds_of_same_question_leave_one_spark(tmp_path):
    path = tmp_path / "sparks.json"
    sparks = [spark(FIRST["question"], f"Revision {i}") for i in range(10)]
    processes = [subprocess.Popen(command(path, spark), stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE) for spark in sparks]
    for process in processes:
        stdout, stderr = process.communicate(timeout=30)
        assert process.returncode == 0, stderr
        assert stdout.startswith(b"added ")
    written = json.loads(path.read_bytes())
    assert len(written) == 1
    assert {k: v for k, v in written[0].items() if k != "id"} in sparks
    assert others(tmp_path) == []


def test_written_file_passes_spark_id_and_the_schema(tmp_path):
    path = tmp_path / "sparks.json"
    for spark in (FIRST, SECOND):
        assert add(path, spark).returncode == 0
    assert spark_id_mod.main(["spark_id.py", str(path)]) == 0
    schema = json.loads((ROOT / "sparks.schema.json").read_bytes())
    Draft202012Validator(schema).validate(json.loads(path.read_bytes()))


@posix
def test_a_file_name_near_the_length_limit_works(tmp_path):
    path = tmp_path / ("s" * 246 + ".json")  # 251 bytes; most file systems allow 255
    assert add(path, FIRST).returncode == 0
    assert json.loads(path.read_bytes()) == [stored(FIRST)]
    assert others(tmp_path, path.name) == []


# rejections: --json

DROP = object()


def _payload(**changes):
    spark = {**FIRST, **changes}
    return json.dumps({key: value for key, value in spark.items() if value is not DROP})


def _raw_question(raw):
    """A payload whose question is the raw JSON text raw."""
    return _payload(question="RAW").replace('"RAW"', raw)


BAD_INPUT = [
    pytest.param("{", "--json: invalid JSON: ", id="truncated"),
    pytest.param("", "--json: invalid JSON: ", id="empty"),
    pytest.param(_payload() + " x", "--json: invalid JSON: Extra data", id="trailing-data"),
    pytest.param(_raw_question("NaN"), "--json: NaN is not valid JSON", id="nan"),
    pytest.param(_raw_question("9" * 5000), "--json: number has too many digits", id="huge-int"),
    pytest.param(json.dumps([FIRST]), "--json: expected one JSON object, a single spark", id="array"),
    pytest.param('"text"', "--json: expected one JSON object, a single spark", id="string"),
    pytest.param(
        _payload()[:-1] + ', "question": "again"}',
        "--json: duplicate key 'question'",
        id="duplicate-key",
    ),
    pytest.param(
        _payload(answer=DROP), "--json: 'answer' is a required property", id="missing-answer"
    ),
    pytest.param(
        _payload(extra=1),
        "--json: Additional properties are not allowed ('extra' was unexpected)",
        id="extra-key",
    ),
    pytest.param(
        _payload(type="spark"),
        "--json: type: 'spark' is not one of ['s', 'p', 'a', 'r', 'k']",
        id="wrong-type",
    ),
    pytest.param(
        _payload(type="SPARK"),
        "--json: type: 'spark' is not one of ['s', 'p', 'a', 'r', 'k']",
        id="type-spark-word",
    ),
    pytest.param(
        _payload(question=1), "--json: question: 1 is not of type 'string'", id="question-int"
    ),
    pytest.param(_raw_question("[" * 500 + "]" * 500), "--json: question: ", id="question-deep"),
    pytest.param(
        _payload(answer=None), "--json: answer: None is not of type 'string'", id="answer-null"
    ),
    pytest.param(
        _payload(id="0" * 16),
        "--json: id is assigned by sparks on add; leave it out",
        id="id-assigned-by-sparks",
    ),
    pytest.param(
        _payload(question="\ud800"),
        "--json: question and answer must be valid UTF-8 text",
        id="lone-surrogate",
    ),
]


@pytest.mark.parametrize("existing", [False, True], ids=["no-file", "existing-file"])
@pytest.mark.parametrize(("payload", "message"), BAD_INPUT)
def test_rejects_bad_json_without_touching_the_file(tmp_path, existing, payload, message):
    path = tmp_path / "sparks.json"
    before = seed(path, [SECOND]) if existing else None
    assert_rejected(add(path, payload), f"sparks: {message}")
    if existing:
        assert path.read_bytes() == before
    else:
        assert not path.exists()
    assert others(tmp_path) == []


@posix
def test_rejects_undecodable_argv_bytes_cleanly(tmp_path):
    path = tmp_path / "sparks.json"
    payload = b'{"type": "s", "question": "\xff", "answer": "a"}'
    result = subprocess.run(
        [sys.executable, str(BIN), "add", "--path", str(path), "--json", payload],
        capture_output=True,
        encoding="utf-8",
    )
    assert_rejected(result, "sparks: --json: question and answer must be valid UTF-8 text")
    assert not path.exists()


# rejections: the file

BAD_FILES = [
    pytest.param(b"", "invalid JSON: Expecting value", id="empty"),
    pytest.param(b"[", "invalid JSON: ", id="truncated"),
    pytest.param(b"\xef\xbb\xbf[]", "invalid JSON: Unexpected UTF-8 BOM", id="bom"),
    pytest.param(b"\xff[]", "file is not UTF-8", id="not-utf8"),
    pytest.param(b"{}", "{} is not of type 'array'", id="object"),
    pytest.param(b"[1]", "[0]: 1 is not of type 'object'", id="not-a-spark"),
    pytest.param(b"[NaN]", "NaN is not valid JSON", id="nan"),
    pytest.param(
        json.dumps([{**FIRST, "id": "0" * 15}]).encode(),
        "[0].id: '000000000000000' is too short",
        id="short-id",
    ),
    pytest.param(
        json.dumps([{**FIRST, "id": "A" * 16}]).encode(),
        "[0].id: 'AAAAAAAAAAAAAAAA' does not match",
        id="uppercase-id",
    ),
    pytest.param(
        json.dumps([{**FIRST, "extra": 1}]).encode(),
        "[0]: Additional properties are not allowed ('extra' was unexpected)",
        id="extra-key",
    ),
    pytest.param(json.dumps([FIRST, FIRST]).encode(), "duplicate id", id="duplicate-spark"),
    pytest.param(
        json.dumps([FIRST])[:-2].encode() + b', "answer": "again"}]',
        "duplicate key 'answer'",
        id="duplicate-key",
    ),
]


@pytest.mark.parametrize(("content", "message"), BAD_FILES)
def test_rejects_an_invalid_existing_file_without_touching_it(tmp_path, content, message):
    path = tmp_path / "sparks.json"
    path.write_bytes(content)
    assert_rejected(add(path, SECOND), f"sparks: {path}: {message}")
    assert path.read_bytes() == content
    assert others(tmp_path) == []


@pytest.mark.parametrize("subject", ["--json", "file"])
def test_deeply_nested_json_is_refused_on_one_line(tmp_path, subject):
    """Python 3.11 to 3.13 hit the recursion limit and 3.14 may not; neither prints a traceback."""
    deep = "[" * 30_000 + "]" * 30_000  # 60 KB stays under the 128 KiB limit on one argument
    path = tmp_path / "sparks.json"
    if subject == "file":
        path.write_text(deep)
    result = add(path, deep if subject == "--json" else FIRST)
    assert_rejected(result, f"sparks: {path if subject == 'file' else '--json'}: ")
    assert path.read_text() == deep if subject == "file" else not path.exists()


def test_schema_problems_are_capped_and_clipped(tmp_path):
    path = tmp_path / "sparks.json"
    path.write_bytes(
        json.dumps([{**spark(f"Q{i}?", "A."), "type": "x"} for i in range(10)]).encode()
    )
    result = add(path, FIRST)
    assert_rejected(result, "[2].type: 'x' is not one of ['s', 'p', 'a', 'r', 'k']; and 7 more")
    assert result.stderr.count("is not one of") == 3
    huge = tmp_path / "package.json"  # an object, not a list of sparks
    huge.write_bytes(json.dumps({f"key{i}": "v" * 100 for i in range(10_000)}).encode())
    result = add(huge, FIRST)
    assert_rejected(result, "is not of type 'array'")
    assert len(result.stderr) < len(str(huge)) + 300


def test_identical_add_succeeds_without_rewriting(tmp_path):
    path = tmp_path / "sparks.json"
    path.write_text(json.dumps([stored(FIRST), SECOND]), encoding="utf-8")
    before = path.read_bytes()
    inode = path.stat().st_ino
    result = add(path, FIRST)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"added {spark_id(FIRST)} to {path}\n"
    assert path.stat().st_ino == inode
    assert path.read_bytes() == before
    assert others(tmp_path) == []


def test_rejects_a_directory_as_the_path(tmp_path):
    assert_rejected(add(tmp_path, FIRST, cwd=tmp_path), f"sparks: {tmp_path}: not a regular file")
    assert list(tmp_path.iterdir()) == []


def test_rejects_a_missing_directory(tmp_path):
    path = tmp_path / "missing" / "sparks.json"
    assert_rejected(
        add(path, FIRST, cwd=tmp_path),
        f"sparks: {path}: directory {tmp_path / 'missing'} does not exist",
    )
    assert list(tmp_path.iterdir()) == []


def test_control_characters_in_the_path_stay_on_one_line(tmp_path):
    path = tmp_path / "two\nlines" / "sparks.json"
    assert_rejected(add(path, FIRST, cwd=tmp_path), "two\\nlines")


@posix
@pytest.mark.skipif(os.name == "posix" and os.geteuid() == 0, reason="root ignores file modes")
def test_rejects_a_read_only_file(tmp_path):
    path = tmp_path / "sparks.json"
    before = seed(path, [FIRST])
    path.chmod(0o444)
    assert_rejected(add(path, SECOND), f"sparks: {path}: Permission denied")
    assert path.read_bytes() == before
    assert others(tmp_path) == []


@pytest.mark.parametrize(
    "args",
    [["add"], ["add", "--path", "x.json"], ["drop"], ["add", "extra"]],
    ids=["no-json", "path-without-json", "unknown-command", "unexpected-arg"],
)
def test_usage_errors_exit_2_without_writing(tmp_path, args):
    result = sparks(*args, cwd=tmp_path)
    assert result.returncode == 2
    assert result.stderr.startswith("usage: sparks")
    assert list(tmp_path.iterdir()) == []


# symlinks, modes, and other file identity


@posix
def test_writes_through_a_symlink(tmp_path):
    shared = tmp_path / "shared.json"
    seed(shared, [FIRST])
    link = tmp_path / "sparks.json"
    link.symlink_to("shared.json")
    assert add(link, SECOND).returncode == 0
    assert link.is_symlink()
    assert json.loads(shared.read_bytes()) == [FIRST, stored(SECOND)]


@posix
@pytest.mark.parametrize("loop", [["sparks.json"], ["sparks.json", "other.json"]], ids=len)
def test_rejects_a_symlink_loop_and_keeps_the_link(tmp_path, loop):
    for name, points_to in zip(loop, loop[1:] + loop[:1], strict=True):
        (tmp_path / name).symlink_to(points_to)
    path = tmp_path / "sparks.json"
    assert_rejected(add(path, FIRST), f"sparks: {path}: cannot resolve symlink")
    assert path.is_symlink()


@posix
def test_dangling_symlink_into_a_missing_directory_names_that_directory(tmp_path):
    link = tmp_path / "sparks.json"
    link.symlink_to("gone/sparks.json")
    assert_rejected(add(link, FIRST), f"directory {tmp_path / 'gone'} does not exist")


@posix
def test_keeps_the_mode_of_an_existing_file(tmp_path):
    path = tmp_path / "sparks.json"
    seed(path, [FIRST])
    path.chmod(0o640)
    assert add(path, SECOND).returncode == 0
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


@posix
def test_new_file_mode_follows_the_umask(tmp_path):
    path = tmp_path / "sparks.json"
    assert add(path, FIRST, umask=0o027).returncode == 0
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


# atomic write


def test_failed_replace_keeps_the_old_file_and_no_temp_file(tmp_path, monkeypatch, capsys):
    path = tmp_path / "sparks.json"
    before = seed(path, [FIRST])

    def fail(src, dst):
        raise OSError(errno.EIO, "simulated I/O error")

    monkeypatch.setattr(os, "replace", fail)
    assert run_main(path, SECOND) == 1
    assert capsys.readouterr().err == f"sparks: {path}: cannot write: simulated I/O error\n"
    assert path.read_bytes() == before
    assert others(tmp_path) == []


def test_disk_full_halfway_through_the_write_keeps_the_old_file(tmp_path, monkeypatch, capsys):
    path = tmp_path / "sparks.json"
    before = seed(path, [FIRST])
    real_fdopen = os.fdopen

    class HalfWriter:
        """Writes half the text to the temp file, then fails like a full disk."""

        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self.handle.close()

        def write(self, text):
            self.handle.write(text[: len(text) // 2])
            self.handle.flush()
            raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(os, "fdopen", lambda fd, *a, **k: HalfWriter(real_fdopen(fd, *a, **k)))
    assert run_main(path, SECOND) == 1
    assert capsys.readouterr().err == f"sparks: {path}: cannot write: No space left on device\n"
    assert path.read_bytes() == before
    assert others(tmp_path) == []


def test_interrupt_before_replace_removes_the_temp_file(tmp_path, monkeypatch):
    path = tmp_path / "sparks.json"
    before = seed(path, [FIRST])

    def interrupt(src, dst):
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "replace", interrupt)
    with pytest.raises(KeyboardInterrupt):
        run_main(path, SECOND)
    assert path.read_bytes() == before
    assert others(tmp_path) == []


@posix
def test_kill_before_replace_keeps_the_old_file_and_the_next_add_works(tmp_path):
    """SIGKILL skips all cleanup: the old file stays whole, and the temp and lock files stay."""
    path = tmp_path / "sparks.json"
    before = seed(path, [FIRST])
    die_at_replace = (
        "import os, runpy, signal, sys\n"
        "os.replace = lambda src, dst: os.kill(os.getpid(), signal.SIGKILL)\n"
        "sys.argv = sys.argv[1:]\n"
        "runpy.run_path(sys.argv[0], run_name='__main__')\n"
    )
    argv = ["add", "--path", str(path), "--json", json.dumps(SECOND)]
    result = subprocess.run(
        [sys.executable, "-c", die_at_replace, str(BIN), *argv], capture_output=True
    )
    assert result.returncode == -signal.SIGKILL
    assert path.read_bytes() == before
    leftovers = set(others(tmp_path))
    assert ".sparks.lock" in leftovers
    (temp,) = leftovers - {".sparks.lock"}
    assert temp.startswith(".sparks-") and temp.endswith(".tmp")
    # The dead process's lock went with it; the next add takes the file and removes it.
    assert add(path, SECOND).returncode == 0
    assert json.loads(path.read_bytes()) == [FIRST, stored(SECOND)]
    assert others(tmp_path) == [temp]


def test_invalid_new_content_never_replaces_the_file(tmp_path, monkeypatch, capsys):
    path = tmp_path / "sparks.json"
    before = seed(path, [FIRST])
    monkeypatch.setattr(cli, "render", lambda sparks: '[{"type": "s"}]\n')
    assert run_main(path, SECOND) == 1
    assert capsys.readouterr().err.startswith(f"sparks: {path} (new content): [0]: ")
    assert path.read_bytes() == before
    assert others(tmp_path) == []


@pytest.mark.parametrize(
    ("intruder", "message"),
    [
        ("[]\n", "written, but another program changed it before it was read back"),
        ("[", "written, but invalid when read back: invalid JSON: "),
    ],
    ids=["valid-but-different", "invalid"],
)
def test_a_file_changed_after_replace_exits_3(tmp_path, monkeypatch, capsys, intruder, message):
    path = tmp_path / "sparks.json"
    seed(path, [FIRST])
    real_replace = os.replace

    def replace_then_clobber(src, dst):
        real_replace(src, dst)
        Path(dst).write_bytes(intruder.encode())

    monkeypatch.setattr(os, "replace", replace_then_clobber)
    assert run_main(path, SECOND) == 3
    assert capsys.readouterr().err.startswith(f"sparks: {path}: {message}")


# the lock


@posix
def test_concurrent_adds_all_land(tmp_path):
    sparks = [spark(f"Question {i}?", f"Answer {i}.") for i in range(20)]
    children = [
        subprocess.Popen(
            [sys.executable, str(BIN), "add", "--json", json.dumps(spark)],
            cwd=tmp_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for spark in sparks
    ]
    assert [child.wait(timeout=120) for child in children] == [0] * len(sparks)
    written = json.loads((tmp_path / "sparks.json").read_bytes())
    assert sorted(written, key=lambda r: r["question"]) == sorted(map(stored, sparks), key=lambda r: r["question"])
    assert others(tmp_path) == []


@posix
def test_an_add_waits_for_the_lock_file_the_path_names(tmp_path):
    """A waiter that wakes up holding a removed lock file must wait for the new one."""
    import fcntl

    def take_lock():
        fd = os.open(lock, os.O_RDWR | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd

    path = tmp_path / "sparks.json"
    before = seed(path, [FIRST])
    lock = tmp_path / ".sparks.lock"
    first_holder = take_lock()
    child = subprocess.Popen(command(path, SECOND), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            child.wait(timeout=1)  # blocked on the first holder's lock file
        os.unlink(lock)  # the first holder lets go the way sparks does: remove, then unlock
        second_holder = take_lock()  # and another add takes a fresh lock file at once
        os.close(first_holder)
        with pytest.raises(subprocess.TimeoutExpired):
            child.wait(timeout=1)  # woke up on the removed file, so it waits again
        assert path.read_bytes() == before
        os.unlink(lock)
        os.close(second_holder)
        assert child.wait(timeout=60) == 0
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
    assert json.loads(path.read_bytes()) == [FIRST, stored(SECOND)]
    assert others(tmp_path) == []


# stdout and stderr


@posix
def test_closed_stdout_does_not_turn_a_write_into_a_failure(tmp_path):
    path = tmp_path / "sparks.json"
    result = subprocess.run(
        command(path, FIRST),
        stderr=subprocess.PIPE,
        encoding="utf-8",
        preexec_fn=lambda: os.close(1),
    )
    assert (result.returncode, result.stderr) == (0, "")
    assert json.loads(path.read_bytes()) == [stored(FIRST)]


@posix
def test_broken_pipe_on_stdout_does_not_turn_a_write_into_a_failure(tmp_path):
    path = tmp_path / "sparks.json"
    read_end, write_end = os.pipe()
    os.close(read_end)  # the reader is gone before sparks writes anything
    try:
        result = subprocess.run(
            command(path, FIRST),
            stdout=write_end,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )
    finally:
        os.close(write_end)
    assert (result.returncode, result.stderr) == (0, "")
    assert json.loads(path.read_bytes()) == [stored(FIRST)]


def test_a_path_stdout_cannot_encode_is_escaped(tmp_path):
    path = tmp_path / "café.json"
    result = add(path, FIRST, env={"PYTHONIOENCODING": "ascii:strict"})
    shown = str(path).encode("ascii", "backslashreplace").decode("ascii")
    assert (result.returncode, result.stdout) == (0, f"added {spark_id(FIRST)} to {shown}\n")
    assert json.loads(path.read_bytes()) == [stored(FIRST)]


# help and the uv entry point


def test_missing_command_exits_2_without_writing(tmp_path):
    result = sparks(cwd=tmp_path)
    assert result.returncode == 2
    assert result.stderr.startswith("usage: sparks")
    assert list(tmp_path.iterdir()) == []


def test_command_help_names_sparks_add(tmp_path):
    result = sparks("--help", cwd=tmp_path)
    assert (result.returncode, result.stderr) == (0, "")
    text = " ".join(result.stdout.split())
    assert "{add,herdr}" in text or " add " in f" {text} "
    assert "entry" not in text
    assert "record" not in text
    add_help = sparks("add", "--help", cwd=tmp_path)
    assert add_help.returncode == 0
    add_text = " ".join(add_help.stdout.split())
    assert "list of sparks" in add_text
    assert "record" not in add_text


def test_add_create_append_replace_and_idempotent_share_one_list(tmp_path):
    path = tmp_path / "sparks.json"

    def invoke(incoming):
        result = sparks("add", "--json", json.dumps(incoming), cwd=tmp_path)
        assert (result.returncode, result.stderr) == (0, "")
        return result

    created = invoke(FIRST)
    assert created.stdout == f"added {spark_id(FIRST)} to sparks.json\n"
    assert json.loads(path.read_bytes()) == [stored(FIRST)]
    invoke(SECOND)
    assert json.loads(path.read_bytes()) == [stored(FIRST), stored(SECOND)]
    revised = spark(FIRST["question"], "Updated verbatim answer.", "R")
    replaced = invoke(revised)
    expected = {**revised, "type": "r", "id": spark_id(FIRST)}
    assert replaced.stdout == created.stdout
    assert json.loads(path.read_bytes()) == [expected, stored(SECOND)]
    before, inode = path.read_bytes(), path.stat().st_ino
    assert invoke(revised).stdout == created.stdout
    assert (path.read_bytes(), path.stat().st_ino) == (before, inode)
    assert others(tmp_path) == []


def test_help_shows_the_usage_exit_codes_and_exact_replace_semantics(tmp_path):
    result = sparks("add", "--help", cwd=tmp_path)
    assert result.returncode == 0
    assert result.stdout.startswith("usage: sparks add [-h] [--path <path>] --json <json>\n")
    assert "Add or replace one spark in a list of sparks." in result.stdout
    assert "one spark:" in result.stdout
    assert "record" not in result.stdout
    assert "exit status: 0 added or replaced; 1 refused, nothing written; 2 usage error; 3 written" in (
        result.stdout
    )
    assert "An exact question match replaces the entire spark" in result.stdout
    assert "Multiple exact matches are" in result.stdout
    assert "An identical spark that already has its id" in result.stdout


@posix
@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv on PATH")
def test_runs_as_an_executable_uv_script(tmp_path):
    result = subprocess.run(
        [str(BIN), "add", "--json", json.dumps(FIRST)],
        cwd=tmp_path,
        capture_output=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"added {spark_id(FIRST)} to sparks.json\n"
    assert json.loads((tmp_path / "sparks.json").read_bytes()) == [stored(FIRST)]



def test_post_call_self_healing_rule_is_packaged():
    """The always-on rule ships and points agents at sparks-postcall after hang-up."""
    rule = ROOT / "rules" / "post-call-self-healing.mdc"
    text = rule.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "alwaysApply: true" in text
    assert "description:" in text.split("---", 2)[1]
    assert "sparks-postcall" in text
    assert "disable-model-invocation" in text
    assert "skills/sparks-postcall/SKILL.md" in text
    assert "/sparks-postcall" in text
    assert "not in `spark-voice`" in text


def test_spark_voice_hang_up_hands_off_to_sparks_postcall():
    """Hang-up does no post-call work and opens sparks-postcall consistently with the rule."""
    voice = (ROOT / "skills" / "spark-voice" / "SKILL.md").read_text(encoding="utf-8")
    hang = voice.split("### Hang-up", 1)[1].split("\n## ", 1)[0]
    assert "This skill does no post-call work" in hang
    assert "post-call protocol lives only in `sparks-postcall`" in hang
    assert "../sparks-postcall/SKILL.md" in hang
    assert "/sparks-postcall" in hang
    assert "tell the user to run the post-call skill" not in hang


def test_spark_verification_is_read_only_generic_skill():
    """spark-verification verifies a PR/branch against sparks.json; no create/maintain modes."""
    skill = ROOT / "skills" / "spark-verification" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    fm, body = text.split("---", 2)[1], text.split("---", 2)[2]
    assert "name: spark-verification" in fm
    assert "description:" in fm
    assert "disable-model-invocation: true" in fm
    assert "sparks.json" in body
    assert "Read-only" in body or "read-only" in body
    assert "never opens pull requests" in body or "never open" in body.lower()
    assert "create-verification-skill" not in body.split("## Out of scope", 1)[0]
    assert "maintain-verification-skill" not in body.split("## Out of scope", 1)[0]
    assert "Headless" not in body.split("## Out of scope", 1)[0]
    assert ".cursor/skills" not in body
    assert "ancestor" in body.lower() or "ancestors" in body.lower()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "spark-verification` is read-only" in readme or "spark-verification` is a separate read-only" in readme
    assert "is an adapter over the last two" not in readme
    discuss = (ROOT / "skills" / "sparks-discuss" / "SKILL.md").read_text(encoding="utf-8")
    assert "If `/spark-verification` started this session" not in discuss


def test_blocker_clearing_rule_is_still_packaged():
    rule = ROOT / "rules" / "blocker-clearing.mdc"
    text = rule.read_text(encoding="utf-8")
    assert "alwaysApply: true" in text
    assert "Stop and deliberate" in text
    assert "sparks-discuss" in text


# herdr snapshot: all commands use an isolated, argv-logging fake on PATH.

HERDR_GROUPS = ("workspace", "tab", "pane", "agent")
HERDR_TABLES = ("workspaces", "tabs", "panes", "agents")
HERDR_KEYS = {
    "workspaces": "workspace_id", "tabs": "tab_id", "panes": "pane_id", "agents": "name",
}
HERDR_COLUMNS = {
    "workspaces": (
        "workspace_id label number active_tab_id agent_status focused pane_count tab_count raw_json"
    ).split(),
    "tabs": "tab_id workspace_id label number agent_status focused pane_count raw_json".split(),
    "panes": (
        "pane_id workspace_id tab_id cwd foreground_cwd agent_status focused revision terminal_id "
        "terminal_title terminal_title_stripped agent agent_session_agent agent_session_kind "
        "agent_session_source agent_session_value restore_error scroll_offset_from_bottom "
        "scroll_max_offset_from_bottom scroll_viewport_rows raw_json"
    ).split(),
    "agents": (
        "name pane_id workspace_id tab_id agent agent_status cwd foreground_cwd focused "
        "interactive_ready revision terminal_id terminal_title terminal_title_stripped "
        "completion_seq state_change_seq screen_detection_skipped agent_session_agent "
        "agent_session_kind agent_session_source agent_session_value raw_json"
    ).split(),
}
HERDR_BOOL_COLUMNS = {"focused", "interactive_ready", "screen_detection_skipped"}
HERDR_INT_COLUMNS = {
    "number", "pane_count", "tab_count", "revision", "completion_seq", "state_change_seq",
    "scroll_offset_from_bottom", "scroll_max_offset_from_bottom", "scroll_viewport_rows",
}
CAPTURED_AT = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z"


def herdr_rows():
    """Live-contract shapes, with only generic cwd/session values and opaque ids."""
    pi_session = {
        "agent": "pi", "kind": "path", "source": "herdr:pi", "value": "/tmp/session.jsonl",
    }
    claude_session = {
        "agent": "claude", "kind": "id", "source": "herdr:claude",
        "value": "04ede96e-6c49-40d4-9995-73aaaffcc7ce",
    }
    scroll = {"max_offset_from_bottom": 0, "offset_from_bottom": 0, "viewport_rows": 49}
    pi_pane = {
        "agent": "pi", "agent_session": pi_session, "agent_status": "working",
        "cwd": "/tmp/proj", "focused": False, "foreground_cwd": "/tmp/proj",
        "pane_id": "w3:pX", "revision": 2, "scroll": scroll, "tab_id": "w3:tX",
        "terminal_id": "term_y", "terminal_title": "π - sparks",
        "terminal_title_stripped": "π - sparks", "workspace_id": "w3",
    }
    done_pane = {
        "agent": "claude", "agent_session": claude_session, "agent_status": "done",
        "cwd": "/tmp/proj", "focused": False, "foreground_cwd": "/tmp/proj",
        "pane_id": "w1:pC", "revision": 3, "scroll": scroll, "tab_id": "w1:tB",
        "terminal_id": "term_c", "terminal_title": "✳ spark ID hashing algorithm",
        "terminal_title_stripped": "spark ID hashing algorithm", "workspace_id": "w1",
    }
    rows = {
        "workspaces": [
            {"active_tab_id": "w3:tX", "agent_status": "done", "focused": False,
             "label": "sparks", "number": 3, "pane_count": 13, "tab_count": 13,
             "workspace_id": "w3"},
            {"active_tab_id": "w1:tB", "agent_status": "done", "focused": True,
             "label": "tasks", "number": 6, "pane_count": 2, "tab_count": 2,
             "workspace_id": "w1"},
            {"active_tab_id": "w6:t1", "agent_status": "unknown", "focused": False,
             "label": "restored", "number": 7, "pane_count": 1, "tab_count": 1,
             "workspace_id": "w6"},
        ],
        "tabs": [
            {"agent_status": "working", "focused": False, "label": "state-review",
             "number": 29, "pane_count": 1, "tab_id": "w3:tX", "workspace_id": "w3"},
            {"agent_status": "done", "focused": False, "label": "completed-task",
             "number": 1, "pane_count": 1, "tab_id": "w1:tB", "workspace_id": "w1"},
            {"agent_status": "unknown", "focused": True, "label": "shell",
             "number": 2, "pane_count": 1, "tab_id": "w1:t1", "workspace_id": "w1"},
            {"agent_status": "unknown", "focused": False, "label": "restored",
             "number": 1, "pane_count": 1, "tab_id": "w6:t1", "workspace_id": "w6"},
        ],
        "panes": [
            pi_pane,
            done_pane,
            {"agent_status": "unknown", "cwd": "/tmp/proj", "focused": False,
             "foreground_cwd": "/tmp/proj", "pane_id": "w1:p1", "revision": 1,
             "scroll": scroll, "tab_id": "w1:t1", "terminal_id": "term_x",
             "terminal_title": "shell", "terminal_title_stripped": "shell",
             "workspace_id": "w1"},
            {"agent_status": "unknown", "cwd": "/tmp/proj", "focused": True,
             "pane_id": "w6:p1", "restore_error": "Saved directory is unavailable.",
             "revision": 0, "tab_id": "w6:t1", "terminal_id": "term_z",
             "workspace_id": "w6"},
        ],
        "agents": [
            {key: value for key, value in pi_pane.items() if key != "scroll"} | {
                "interactive_ready": True, "name": "state-review",
                "screen_detection_skipped": True, "state_change_seq": 149,
            },
            {key: value for key, value in done_pane.items() if key != "scroll"} | {
                "completion_seq": 53, "interactive_ready": True,
                "name": "completed-task", "state_change_seq": 53,
            },
        ],
    }
    # Each entity owns its nested fixture objects; changing an agent must not
    # accidentally change its pane and make an earlier list fail instead.
    return {table: [copy.deepcopy(row) for row in values] for table, values in rows.items()}


FAKE_HERDR = r'''
import json
import os
import sys
import time

with open(os.environ["SPARKS_TEST_HERDR_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({
        "argv": sys.argv,
        "socket": os.environ.get("HERDR_SOCKET_PATH"),
        "herdr_env": os.environ.get("HERDR_ENV"),
    }) + "\n")
if len(sys.argv) != 3 or sys.argv[1] not in ("workspace", "tab", "pane", "agent") or sys.argv[2] != "list":
    sys.stderr.write("fake herdr: unexpected argv\n")
    sys.exit(73)
with open(os.environ["SPARKS_TEST_HERDR_RESPONSES"], encoding="utf-8") as config:
    reply = json.load(config)[sys.argv[1]]
time.sleep(reply.get("sleep", 0))
for name, stream in (("stdout", sys.stdout), ("stderr", sys.stderr)):
    if name + "_hex" in reply:
        stream.buffer.write(bytes.fromhex(reply[name + "_hex"]))
    else:
        stream.buffer.write(reply.get(name, "").encode("utf-8"))
    stream.buffer.flush()
sys.exit(reply.get("code", 0))
'''


class FakeHerdr:
    def __init__(self, directory, monkeypatch):
        self.directory = directory
        self.monkeypatch = monkeypatch
        self.bin_dir = directory / "fake-bin"
        self.bin_dir.mkdir()
        self.executable = self.bin_dir / "herdr"
        self.executable.write_text(f"#!{sys.executable}\n" + FAKE_HERDR, encoding="utf-8")
        self.executable.chmod(0o755)
        self.log = directory / "herdr-argv.jsonl"
        self.config = directory / "herdr-responses.json"
        self.home = directory / "home"
        self.xdg = directory / "xdg"
        self.home.mkdir()
        self.xdg.mkdir()
        self.db = directory / "state.sqlite"
        monkeypatch.setenv("PATH", str(self.bin_dir) + os.pathsep + os.environ.get("PATH", ""))
        monkeypatch.setenv("HOME", str(self.home))
        monkeypatch.setenv("XDG_DATA_HOME", str(self.xdg))
        monkeypatch.setenv("SPARKS_HERDR_DB", str(self.db))
        monkeypatch.setenv("SPARKS_TEST_HERDR_LOG", str(self.log))
        monkeypatch.setenv("SPARKS_TEST_HERDR_RESPONSES", str(self.config))
        monkeypatch.setenv("HERDR_SOCKET_PATH", "/tmp/test-herdr.sock")
        monkeypatch.delenv("HERDR_ENV", raising=False)
        monkeypatch.delenv("SPARKS_HERDR_TIMEOUT", raising=False)
        assert shutil.which("herdr") == str(self.executable)
        self.respond()

    def respond(self, rows=None, **overrides):
        self.rows = copy.deepcopy(herdr_rows() if rows is None else rows)
        replies = {
            group: {"stdout": json.dumps({
                "id": "opaque-response", "result": {"type": group + "_list", table: self.rows[table]},
            }, ensure_ascii=False)}
            for group, table in zip(HERDR_GROUPS, HERDR_TABLES)
        }
        for group, override in overrides.items():
            replies[group].update(override)
        self.config.write_text(json.dumps(replies, ensure_ascii=False), encoding="utf-8")

    def run(self, *args, **kwargs):
        kwargs.setdefault("timeout", 15)
        return sparks("herdr", "snapshot", *args, cwd=self.directory, **kwargs)

    @property
    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def assert_calls(self, groups=HERDR_GROUPS):
        # Includes argv[0]: only the fake resolved from our prepended PATH ran.
        assert [call["argv"] for call in self.calls] == [
            [str(self.executable), group, "list"] for group in groups
        ]

    def clear_calls(self):
        self.log.unlink(missing_ok=True)

    def seed(self):
        result = self.run()
        assert_snapshot_success(self, result)
        self.assert_calls()
        self.clear_calls()
        return self.db.read_bytes(), database_dump(self.db)


@pytest.fixture
def fake_herdr(tmp_path, monkeypatch):
    if os.name != "posix":
        pytest.skip("fake executable uses a POSIX shebang")
    return FakeHerdr(tmp_path, monkeypatch)


@pytest.fixture
def saved_snapshot(fake_herdr):
    before = fake_herdr.seed()
    return fake_herdr, before


@pytest.fixture(params=["version-1", "no-meta"])
def delete_snapshot(fake_herdr, request):
    fake = fake_herdr
    fake.seed()
    with contextlib.closing(sqlite3.connect(fake.db)) as db:
        if request.param == "no-meta":
            db.execute("DROP TABLE meta")
            db.commit()
        assert db.execute("PRAGMA journal_mode=DELETE").fetchone()[0] == "delete"
    before = database_dump(fake.db)
    fake.respond(changed_herdr_rows(fake.rows))
    return fake, before


@pytest.fixture(params=["absolute", "uri-characters"])
def unsupported_wal(fake_herdr, request):
    fake = fake_herdr
    shown = str(fake.db) if request.param == "absolute" else "./future#?%23.sqlite"
    target = fake.directory / shown
    leave_wal = """
import os
import sqlite3
import sys

db = sqlite3.connect(sys.argv[1])
assert db.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
db.execute("PRAGMA wal_autocheckpoint=0")
db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
db.execute("INSERT INTO meta VALUES ('schema_version', '2')")
db.execute("CREATE TABLE future_inventory (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
db.execute("INSERT INTO future_inventory VALUES ('opaque-id', 'committed future data')")
db.commit()
os._exit(0)
"""
    child = subprocess.run(
        [sys.executable, "-c", leave_wal, str(target)], cwd=fake.directory,
        capture_output=True, encoding="utf-8", timeout=10,
    )
    assert (child.returncode, child.stdout, child.stderr) == (0, "", "")
    files = (target, Path(str(target) + "-wal"), Path(str(target) + "-shm"))
    assert all(path.is_file() for path in files)
    assert files[1].stat().st_size > 32
    # Ignoring WAL exposes the old main file, proving the committed schema
    # was left uncheckpointed rather than merely leaving empty sidecars.
    with contextlib.closing(sqlite3.connect(
        target.absolute().as_uri() + "?mode=ro&immutable=1", uri=True,
    )) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []
    before = {path: path.read_bytes() for path in files[:2]}
    return fake, target, shown, files, before


@contextlib.contextmanager
def snapshot_reader(path):
    # A failed test must not silently create the file it was meant to inspect.
    with contextlib.closing(sqlite3.connect(path.absolute().as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        yield db


def database_dump(path):
    with snapshot_reader(path) as db:
        return tuple(db.iterdump())


def assert_snapshot_unchanged(fake, before):
    if before is None:
        assert not fake.db.exists()
    else:
        assert fake.db.read_bytes() == before[0]
        assert database_dump(fake.db) == before[1]


def assert_invalid_herdr_rows(fake, table, before):
    index = HERDR_TABLES.index(table)
    assert_rejected(fake.run(), f"herdr {HERDR_GROUPS[index]} list: ")
    fake.assert_calls(HERDR_GROUPS[:index + 1])
    assert_snapshot_unchanged(fake, before)


def projected_value(row, column):
    if column.startswith("agent_session_"):
        return row.get("agent_session", {}).get(column.removeprefix("agent_session_"))
    if column.startswith("scroll_"):
        return row.get("scroll", {}).get(column.removeprefix("scroll_"))
    value = row.get(column)
    return int(value) if column in HERDR_BOOL_COLUMNS and value is not None else value


def assert_snapshot_entities(path, rows):
    with snapshot_reader(path) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert tables == {"meta", "snapshot", *HERDR_TABLES}
        assert db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == "1"
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        for table in HERDR_TABLES:
            columns = [row[1] for row in db.execute(f"PRAGMA table_info({table})")]
            assert columns == HERDR_COLUMNS[table]
            stored = {row[HERDR_KEYS[table]]: dict(row) for row in db.execute(f"SELECT * FROM {table}")}
            expected = {row[HERDR_KEYS[table]]: row for row in rows[table]}
            assert stored.keys() == expected.keys()
            for key, original in expected.items():
                for column in columns:
                    value = stored[key][column]
                    if column == "raw_json":
                        assert json.loads(value) == original
                        for symbol in ("π", "✳"):
                            if symbol in json.dumps(original, ensure_ascii=False):
                                assert symbol in value
                    else:
                        assert value == projected_value(original, column), (table, key, column)
                        if value is not None and column in HERDR_BOOL_COLUMNS | HERDR_INT_COLUMNS:
                            assert type(value) is int
        indexes = {
            "tabs_workspace": ("workspace_id",), "panes_workspace": ("workspace_id",),
            "panes_tab": ("tab_id",), "agents_workspace": ("workspace_id",),
            "agents_status": ("agent_status",),
        }
        for name, columns in indexes.items():
            assert tuple(row[2] for row in db.execute(f"PRAGMA index_info({name})")) == columns
        snapshots = [dict(row) for row in db.execute("SELECT * FROM snapshot")]
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        assert snapshot["id"] == 1
        assert re.fullmatch(CAPTURED_AT, snapshot["captured_at"])
        assert datetime.fromisoformat(snapshot["captured_at"]).utcoffset().total_seconds() == 0
        assert [snapshot[group + "_count"] for group in HERDR_GROUPS] == [
            len(rows[table]) for table in HERDR_TABLES
        ]
        return snapshot


def assert_snapshot_success(fake, result, *, rows=None, db=None, shown_db=None):
    rows = fake.rows if rows is None else rows
    db = fake.db if db is None else db
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    snapshot = assert_snapshot_entities(db, rows)
    shown_db = str(db) if shown_db is None else shown_db
    counts = " ".join(f"{table}={len(rows[table])}" for table in HERDR_TABLES)
    assert result.stdout == f"snapshot {snapshot['captured_at']} {counts} db={shown_db}\n"
    return snapshot


def test_herdr_snapshot_happy_path_columns_nulls_unicode_and_exact_argv(fake_herdr):
    started = datetime.now(timezone.utc)
    snapshot = assert_snapshot_success(fake_herdr, fake_herdr.run())
    finished = datetime.now(timezone.utc)
    # Millisecond formatting truncates the transaction start time by at most 1 ms.
    captured = datetime.fromisoformat(snapshot["captured_at"])
    assert started.timestamp() - 0.001 <= captured.timestamp() <= finished.timestamp()
    fake_herdr.assert_calls()
    with snapshot_reader(fake_herdr.db) as db:
        restored = db.execute("SELECT * FROM panes WHERE pane_id='w6:p1'").fetchone()
        assert restored["restore_error"] == "Saved directory is unavailable."
        for column in ("foreground_cwd", "terminal_title", "terminal_title_stripped", "agent",
                       "agent_session_value", "scroll_viewport_rows"):
            assert restored[column] is None
        pi = db.execute("SELECT * FROM agents WHERE name='state-review'").fetchone()
        done = db.execute("SELECT * FROM agents WHERE name='completed-task'").fetchone()
        assert pi["completion_seq"] is None and pi["screen_detection_skipped"] == 1
        assert done["completion_seq"] == 53 and done["screen_detection_skipped"] is None
        assert db.execute("SELECT agent_status FROM workspaces WHERE workspace_id='w3'").fetchone()[0] == "done"
        assert pi["agent_status"] == "working"  # not a recomputed workspace rollup
        assert db.execute("SELECT COUNT(*) FROM panes WHERE agent IS NULL").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM agents").fetchone()[0] == 2  # no synthesized agents


def changed_herdr_rows(rows):
    changed = copy.deepcopy(rows)
    for table in HERDR_TABLES:
        changed[table] = [row for row in changed[table] if row["workspace_id"] != "w1"]
    changed["agents"][0]["agent_status"] = "blocked"
    changed["agents"][0]["interactive_ready"] = False
    changed["panes"][0]["agent_status"] = "blocked"
    new_agent = {**changed["agents"][0], "name": "new-agent", "pane_id": "w3:pNew",
                 "agent_status": "working", "revision": 4}
    changed["agents"].append(new_agent)
    changed["panes"].append({
        **changed["panes"][0], "pane_id": "w3:pNew", "agent_status": "working", "revision": 4,
    })
    return changed


def test_herdr_snapshot_upserts_and_prunes_every_table(saved_snapshot):
    fake, _ = saved_snapshot
    with snapshot_reader(fake.db) as db:
        old_time = db.execute("SELECT captured_at FROM snapshot").fetchone()[0]
    fake.respond(changed_herdr_rows(fake.rows))
    time.sleep(0.01)
    snapshot = assert_snapshot_success(fake, fake.run())
    fake.assert_calls()
    assert snapshot["captured_at"] > old_time
    with snapshot_reader(fake.db) as db:
        for table in HERDR_TABLES:
            assert db.execute(f"SELECT COUNT(*) FROM {table} WHERE workspace_id='w1'").fetchone()[0] == 0
        assert db.execute("SELECT agent_status FROM agents WHERE name='state-review'").fetchone()[0] == "blocked"
        assert db.execute("SELECT agent_status FROM agents WHERE name='new-agent'").fetchone()[0] == "working"


@pytest.mark.parametrize("change", ["rename-on-same-pane", "move-to-new-pane", "swap-panes"])
def test_herdr_agent_pane_reassignment_and_swap_preserve_unique_inventory(saved_snapshot, change):
    fake, _ = saved_snapshot
    rows = herdr_rows()
    first, second = copy.deepcopy(rows["agents"])
    if change == "rename-on-same-pane":
        rows["agents"][0]["name"] = "renamed-review"
    elif change == "move-to-new-pane":
        new_pane_id = "w3:pReplacement"
        rows["agents"][0]["pane_id"] = new_pane_id
        rows["panes"][0]["pane_id"] = new_pane_id
    else:
        # Both names stay, but each now owns the other's old pane. A naive
        # sequential upsert hits agents.pane_id UNIQUE before the second update.
        rows["agents"] = [
            {**second, "name": first["name"]}, {**first, "name": second["name"]},
        ]
    fake.respond(rows)
    assert_snapshot_success(fake, fake.run())
    fake.assert_calls()
    with snapshot_reader(fake.db) as db:
        owners = dict(db.execute("SELECT name, pane_id FROM agents"))
        assert owners == {row["name"]: row["pane_id"] for row in rows["agents"]}
        assert db.execute("SELECT COUNT(DISTINCT pane_id) FROM agents").fetchone()[0] == 2
        if change == "rename-on-same-pane":
            assert first["name"] not in owners
            assert owners["renamed-review"] == first["pane_id"]
        elif change == "move-to-new-pane":
            assert first["pane_id"] not in owners.values()
            assert db.execute("SELECT COUNT(*) FROM panes WHERE pane_id=?", (first["pane_id"],)).fetchone()[0] == 0
        else:
            assert owners[first["name"]] == second["pane_id"]
            assert owners[second["name"]] == first["pane_id"]


def test_herdr_identical_second_snapshot_replaces_single_snapshot_row(saved_snapshot):
    fake, _ = saved_snapshot
    with snapshot_reader(fake.db) as db:
        old_time = db.execute("SELECT captured_at FROM snapshot").fetchone()[0]
    time.sleep(0.01)
    snapshot = assert_snapshot_success(fake, fake.run())
    assert snapshot["captured_at"] > old_time
    fake.assert_calls()


@pytest.mark.parametrize("existing", [False, True])
def test_herdr_empty_lists_are_success_and_remove_previous_inventory(fake_herdr, existing):
    if existing:
        fake_herdr.seed()
    fake_herdr.respond({table: [] for table in HERDR_TABLES})
    assert_snapshot_success(fake_herdr, fake_herdr.run())
    fake_herdr.assert_calls()


@pytest.mark.parametrize("existing", [False, True])
def test_herdr_missing_on_path_does_not_create_or_modify_database(fake_herdr, existing):
    before = fake_herdr.seed() if existing else None
    empty_bin = fake_herdr.directory / "empty-bin"
    empty_bin.mkdir()
    fake_herdr.monkeypatch.setenv("PATH", str(empty_bin))
    result = fake_herdr.run()
    assert (result.returncode, result.stdout, result.stderr) == (
        1, "", "sparks: herdr: command not found\n",
    )
    fake_herdr.assert_calls(())
    assert_snapshot_unchanged(fake_herdr, before)


@pytest.mark.parametrize("error_first", [False, True], ids=["id-first", "error-first"])
@pytest.mark.parametrize("existing", [False, True])
def test_herdr_server_not_running_json_is_sanitized_and_stops(fake_herdr, existing, error_first):
    before = fake_herdr.seed() if existing else None
    error = {"code": "server_not_running", "message": (
        "no herdr server is running at /tmp/no-such-herdr.sock; run `herdr` to start or attach it"
    )}
    envelope = ({"error": error, "id": "cli:workspace:list"} if error_first else
                {"id": "cli:workspace:list", "error": error})
    fake_herdr.respond(workspace={"stdout": "", "stderr": json.dumps(envelope), "code": 1})
    result = fake_herdr.run()
    assert (result.returncode, result.stdout, result.stderr) == (
        1, "", "sparks: herdr is not running\n",
    )
    fake_herdr.assert_calls(("workspace",))
    assert_snapshot_unchanged(fake_herdr, before)


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_herdr_server_not_running_text_is_sanitized(saved_snapshot, stream):
    fake, before = saved_snapshot
    fake.respond(tab={"stdout": "", stream: "the server is not running; run `herdr` to start or attach it", "code": 2})
    result = fake.run()
    assert (result.returncode, result.stdout, result.stderr) == (
        1, "", "sparks: herdr is not running\n",
    )
    fake.assert_calls(("workspace", "tab"))
    assert_snapshot_unchanged(fake, before)


@pytest.mark.parametrize("group", HERDR_GROUPS)
def test_herdr_failed_list_stops_at_first_failure_and_keeps_snapshot(saved_snapshot, group):
    fake, before = saved_snapshot
    fake.respond(**{group: {"stdout": "", "stderr": f"usage: herdr {group} list\n", "code": 2}})
    result = fake.run()
    assert_rejected(result, f"herdr {group} list: ")
    assert f"usage: herdr {group} list" in result.stderr
    fake.assert_calls(HERDR_GROUPS[:HERDR_GROUPS.index(group) + 1])
    assert_snapshot_unchanged(fake, before)


@pytest.mark.parametrize(("group", "stdout"), [
    pytest.param("workspace", "not JSON", id="not-json"),
    pytest.param("workspace", "{}", id="missing-result"),
    pytest.param("tab", '{"result":{"type":"pane_list","tabs":[]}}', id="wrong-type"),
    pytest.param("pane", '{"result":{"type":"pane_list"}}', id="missing-array"),
    pytest.param("agent", '{"result":{"type":"agent_list","agents":{}}}', id="not-array"),
    pytest.param("workspace", "[]", id="top-array"),
    pytest.param("workspace", "null", id="top-null"),
    pytest.param("tab", '{"result":[]}', id="result-array"),
    pytest.param("pane", '{"result":null}', id="result-null"),
    pytest.param("agent", '{"result":{"agents":[]}}', id="missing-type"),
    pytest.param("workspace", '{"result":{"type":"workspace_list","workspaces":[]}} junk', id="trailing-data"),
])
@pytest.mark.parametrize("existing", [False, True])
def test_herdr_invalid_envelopes_never_write(fake_herdr, existing, group, stdout):
    before = fake_herdr.seed() if existing else None
    fake_herdr.respond(**{group: {"stdout": stdout}})
    assert_rejected(fake_herdr.run(), f"herdr {group} list: ")
    fake_herdr.assert_calls(HERDR_GROUPS[:HERDR_GROUPS.index(group) + 1])
    assert_snapshot_unchanged(fake_herdr, before)


@pytest.mark.parametrize(("field", "value"), [("pane_id", 3), ("revision", True), ("focused", 0)])
@pytest.mark.parametrize("existing", [False, True])
def test_herdr_required_bad_pane_types_never_write(fake_herdr, existing, field, value):
    before = fake_herdr.seed() if existing else None
    rows = herdr_rows()
    rows["panes"][0][field] = value
    fake_herdr.respond(rows)
    assert_invalid_herdr_rows(fake_herdr, "panes", before)


@pytest.mark.parametrize(("table", "field"), [
    ("workspaces", "workspace_id"), ("tabs", "tab_id"), ("tabs", "workspace_id"),
    ("panes", "pane_id"), ("panes", "workspace_id"), ("panes", "tab_id"),
    ("agents", "name"), ("agents", "pane_id"), ("agents", "workspace_id"), ("agents", "tab_id"),
])
@pytest.mark.parametrize("value", [DROP, None, "", 1, False], ids=["missing", "null", "empty", "int", "bool"])
def test_herdr_all_identity_fields_are_required_nonempty_strings(saved_snapshot, table, field, value):
    fake, before = saved_snapshot
    rows = herdr_rows()
    if value is DROP:
        rows[table][0].pop(field)
    else:
        rows[table][0][field] = value
    fake.respond(rows)
    assert_invalid_herdr_rows(fake, table, before)


@pytest.mark.parametrize("table", HERDR_TABLES)
@pytest.mark.parametrize("value", [None, [], "not an object", 1])
def test_herdr_every_array_element_must_be_an_object(saved_snapshot, table, value):
    fake, before = saved_snapshot
    rows = herdr_rows()
    rows[table].append(value)
    fake.respond(rows)
    assert_invalid_herdr_rows(fake, table, before)


@pytest.mark.parametrize(("table", "field"), [
    ("workspaces", "workspace_id"), ("tabs", "tab_id"), ("panes", "pane_id"),
    ("agents", "name"), ("agents", "pane_id"),
])
@pytest.mark.parametrize("existing", [False, True])
def test_herdr_duplicate_primary_keys_and_agent_pane_ids_fail(fake_herdr, existing, table, field):
    before = fake_herdr.seed() if existing else None
    rows = herdr_rows()
    duplicate = copy.deepcopy(rows[table][0])
    if table == "agents":
        duplicate["name" if field == "pane_id" else "pane_id"] = "otherwise-unique"
    rows[table].append(duplicate)
    fake_herdr.respond(rows)
    assert_invalid_herdr_rows(fake_herdr, table, before)


# Enumerate the optional query surface independently of the CLI implementation.
HERDR_OPTIONAL_FIELDS = {
    "workspaces": {
        "str": "label active_tab_id agent_status", "int": "number pane_count tab_count",
        "bool": "focused",
    },
    "tabs": {
        "str": "label agent_status", "int": "number pane_count", "bool": "focused",
    },
    "panes": {
        "str": "cwd foreground_cwd agent_status terminal_id terminal_title terminal_title_stripped agent restore_error",
        "int": "revision", "bool": "focused",
    },
    "agents": {
        "str": "agent agent_status cwd foreground_cwd terminal_id terminal_title terminal_title_stripped",
        "int": "revision completion_seq state_change_seq",
        "bool": "focused interactive_ready screen_detection_skipped",
    },
}
BAD_OPTIONAL_FIELDS = [
    pytest.param(table, field, {"str": 7, "int": True, "bool": 1}[kind], id=f"{table}-{field}")
    for table, kinds in HERDR_OPTIONAL_FIELDS.items()
    for kind, fields in kinds.items() for field in fields.split()
] + [
    pytest.param(table, field, 1.0, id=f"{table}-{field}-float")
    for table, kinds in HERDR_OPTIONAL_FIELDS.items() for field in kinds["int"].split()
]


@pytest.mark.parametrize(("table", "field", "value"), BAD_OPTIONAL_FIELDS)
def test_herdr_bad_optional_scalar_types_roll_back(saved_snapshot, table, field, value):
    fake, before = saved_snapshot
    rows = herdr_rows()
    rows[table][0][field] = value
    fake.respond(rows)
    assert_invalid_herdr_rows(fake, table, before)


@pytest.mark.parametrize(("table", "container"), [
    ("panes", "agent_session"), ("agents", "agent_session"), ("panes", "scroll"),
])
@pytest.mark.parametrize("value", [None, [], "wrong", 0, False])
def test_herdr_nested_containers_must_be_objects(saved_snapshot, table, container, value):
    fake, before = saved_snapshot
    rows = herdr_rows()
    rows[table][0][container] = value
    fake.respond(rows)
    assert_invalid_herdr_rows(fake, table, before)


BAD_NESTED_FIELDS = [
    pytest.param(table, "agent_session", field, 9, id=f"{table}-session-{field}")
    for table in ("panes", "agents") for field in ("agent", "kind", "source", "value")
] + [
    pytest.param("panes", "scroll", field, value, id=f"scroll-{field}-{value}")
    for field in ("offset_from_bottom", "max_offset_from_bottom", "viewport_rows")
    for value in (True, 1.0)
]


@pytest.mark.parametrize(("table", "container", "field", "value"), BAD_NESTED_FIELDS)
def test_herdr_bad_nested_field_types_roll_back(saved_snapshot, table, container, field, value):
    fake, before = saved_snapshot
    rows = herdr_rows()
    rows[table][0][container][field] = value
    fake.respond(rows)
    assert_invalid_herdr_rows(fake, table, before)


def test_herdr_last_list_validation_does_not_create_database_or_parents(fake_herdr):
    target = fake_herdr.directory / "uncreated" / "nested" / "state.sqlite"
    rows = herdr_rows()
    rows["agents"][-1]["interactive_ready"] = 1
    fake_herdr.respond(rows)
    assert_rejected(fake_herdr.run("--db", str(target)), "herdr agent list: ")
    fake_herdr.assert_calls()
    assert not target.parent.parent.exists()
    assert not fake_herdr.db.exists()


@pytest.mark.parametrize("form", ["omitted", "null-scalars", "empty-nested", "empty-strings"])
def test_herdr_optional_absence_null_and_empty_strings_are_preserved(fake_herdr, form):
    rows = herdr_rows()
    for table, kinds in HERDR_OPTIONAL_FIELDS.items():
        for row in rows[table]:
            for kind, fields in kinds.items():
                for field in fields.split():
                    if form in ("omitted", "empty-nested"):
                        row.pop(field, None)
                    else:
                        row[field] = "" if kind == "str" and form == "empty-strings" else None
            for container, fields in (
                ("agent_session", ("agent", "kind", "source", "value")),
                ("scroll", ("offset_from_bottom", "max_offset_from_bottom", "viewport_rows")),
            ):
                if table not in ("panes", "agents") or (container == "scroll" and table != "panes"):
                    continue
                if form == "omitted":
                    row.pop(container, None)
                elif form == "empty-nested":
                    row[container] = {}
                else:
                    row[container] = {
                        field: "" if container == "agent_session" and form == "empty-strings" else None
                        for field in fields
                    }
    fake_herdr.respond(rows)
    assert_snapshot_success(fake_herdr, fake_herdr.run())
    fake_herdr.assert_calls()


@pytest.mark.parametrize("table", HERDR_TABLES)
def test_herdr_unknown_status_and_extra_keys_are_retained(fake_herdr, table):
    rows = herdr_rows()
    rows[table][0]["agent_status"] = "future-status"
    rows[table][0]["future_field"] = {"title": "π ✳", "values": [True, None, 3]}
    if table in ("panes", "agents"):
        rows[table][0]["agent_session"]["future_field"] = ["retained"]
    if table == "panes":
        rows[table][0]["scroll"]["future_field"] = "retained"
    fake_herdr.respond(rows)
    assert_snapshot_success(fake_herdr, fake_herdr.run())
    fake_herdr.assert_calls()


def test_herdr_torn_workspace_tab_and_pane_references_are_not_dropped(fake_herdr):
    rows = herdr_rows()
    rows["tabs"][0]["workspace_id"] = "absent-workspace"
    rows["panes"][0]["workspace_id"] = "absent-workspace"
    rows["panes"][0]["tab_id"] = "absent-tab"
    rows["agents"][0]["workspace_id"] = "absent-workspace"
    rows["agents"][0]["tab_id"] = "absent-tab"
    rows["agents"][0]["pane_id"] = "absent-pane"
    fake_herdr.respond(rows)
    assert_snapshot_success(fake_herdr, fake_herdr.run())
    fake_herdr.assert_calls()  # no retries to mend a sequential-list tear
    with snapshot_reader(fake_herdr.db) as db:
        for table in HERDR_TABLES:
            assert list(db.execute(f"PRAGMA foreign_key_list({table})")) == []


@pytest.mark.parametrize("choice", ["argument", "environment", "xdg", "home", "empty-xdg"])
def test_herdr_database_path_precedence_is_isolated(fake_herdr, choice):
    fake = fake_herdr
    explicit = fake.directory / "explicit.sqlite"
    args = ()
    if choice == "argument":
        expected = explicit
        args = ("--db", str(explicit))
    elif choice == "environment":
        expected = fake.db
    else:
        fake.monkeypatch.delenv("SPARKS_HERDR_DB")
        if choice == "xdg":
            expected = fake.xdg / "sparks" / "herdr-state.sqlite"
        else:
            if choice == "home":
                fake.monkeypatch.delenv("XDG_DATA_HOME")
            else:
                fake.monkeypatch.setenv("XDG_DATA_HOME", "")
            expected = fake.home / ".local" / "share" / "sparks" / "herdr-state.sqlite"
    assert_snapshot_success(fake, fake.run(*args), db=expected)
    fake.assert_calls()
    # Exactly one database, and only under the fixture's temporary directory.
    assert list(fake.directory.rglob("*.sqlite")) == [expected]


@pytest.mark.parametrize("choice", ["argument", "environment"])
def test_herdr_relative_database_path_output_is_not_resolved(fake_herdr, choice):
    shown = "./relative.sqlite"
    if choice == "argument":
        result = fake_herdr.run("--db", shown)
    else:
        fake_herdr.monkeypatch.setenv("SPARKS_HERDR_DB", shown)
        result = fake_herdr.run()
    assert_snapshot_success(fake_herdr, result, db=fake_herdr.directory / "relative.sqlite", shown_db=shown)
    assert not fake_herdr.db.exists()
    fake_herdr.assert_calls()


@pytest.mark.parametrize("name", ["hash#state.sqlite", "query?mode=rw.sqlite", "percent%23state.sqlite"])
def test_herdr_existing_database_readonly_uri_escapes_reserved_path_characters(fake_herdr, name):
    fake = fake_herdr
    shown = f"./data#?%25/{name}"
    target = fake.directory / shown
    old_snapshot = assert_snapshot_success(fake, fake.run("--db", shown), db=target, shown_db=shown)
    fake.assert_calls()
    fake.clear_calls()
    fake.respond(changed_herdr_rows(fake.rows))
    time.sleep(0.01)
    snapshot = assert_snapshot_success(fake, fake.run("--db", shown), db=target, shown_db=shown)
    assert snapshot["captured_at"] > old_snapshot["captured_at"]
    fake.assert_calls()
    assert not fake.db.exists()
    assert list(fake.directory.rglob("*.sqlite")) == [target]


def test_herdr_creates_parent_directories_and_schema_v1(fake_herdr):
    target = fake_herdr.directory / "new" / "nested" / "state.sqlite"
    result = fake_herdr.run("--db", str(target), umask=0)
    assert_snapshot_success(fake_herdr, result, db=target)
    assert target.read_bytes().startswith(b"SQLite format 3\x00")
    for parent in (target.parent, target.parent.parent):
        assert stat.S_IMODE(parent.stat().st_mode) == 0o755
    fake_herdr.assert_calls()


@pytest.mark.parametrize("kind", ["empty-file", "empty-sqlite"])
def test_herdr_initializes_file_without_meta_in_first_snapshot(fake_herdr, kind):
    if kind == "empty-file":
        fake_herdr.db.touch()
    else:
        with contextlib.closing(sqlite3.connect(fake_herdr.db)) as db:
            db.execute("VACUUM")
        assert fake_herdr.db.read_bytes().startswith(b"SQLite format 3\x00")
    assert_snapshot_success(fake_herdr, fake_herdr.run())
    fake_herdr.assert_calls()


@posix
def test_herdr_new_database_mode_is_private_even_with_permissive_umask(fake_herdr):
    assert_snapshot_success(fake_herdr, fake_herdr.run(umask=0))
    assert stat.S_IMODE(fake_herdr.db.stat().st_mode) == 0o600


@posix
@pytest.mark.parametrize("existing_snapshot", [False, True])
def test_herdr_keeps_existing_database_file_mode(fake_herdr, existing_snapshot):
    if existing_snapshot:
        fake_herdr.seed()
    else:
        fake_herdr.db.touch()
    fake_herdr.db.chmod(0o640)
    assert_snapshot_success(fake_herdr, fake_herdr.run(umask=0o077))
    assert stat.S_IMODE(fake_herdr.db.stat().st_mode) == 0o640


def test_herdr_failed_chmod_does_not_fail_a_successful_snapshot(fake_herdr, monkeypatch, capsys):
    real_chmod = os.chmod
    attempts = []

    def fail_database_chmod(path, mode, *args, **kwargs):
        if Path(path) == fake_herdr.db:
            attempts.append(mode)
            raise OSError(errno.EACCES, "simulated chmod failure")
        return real_chmod(path, mode, *args, **kwargs)

    monkeypatch.setattr(os, "chmod", fail_database_chmod)
    code = cli.main(["herdr", "snapshot"])
    output = capsys.readouterr()
    result = subprocess.CompletedProcess([], code, output.out, output.err)
    assert_snapshot_success(fake_herdr, result)
    assert attempts == [0o600]
    fake_herdr.assert_calls()


def test_herdr_non_sqlite_target_bytes_are_unchanged(fake_herdr):
    content = b"not a SQLite database\n\x00\xff"
    fake_herdr.db.write_bytes(content)
    assert_rejected(fake_herdr.run(), f"{fake_herdr.db}: ")
    assert fake_herdr.db.read_bytes() == content


@pytest.mark.parametrize("version", ["2", "0", "future-version"])
def test_herdr_unsupported_schema_version_changes_nothing(fake_herdr, version):
    with contextlib.closing(sqlite3.connect(fake_herdr.db)) as db:
        db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("INSERT INTO meta VALUES ('schema_version', ?)", (version,))
        db.commit()
    before = fake_herdr.db.read_bytes(), database_dump(fake_herdr.db)
    result = fake_herdr.run()
    assert (result.returncode, result.stdout, result.stderr) == (
        1, "", f"sparks: {fake_herdr.db}: unsupported schema_version {version} (expected 1)\n",
    )
    assert_snapshot_unchanged(fake_herdr, before)


def test_herdr_unsupported_wal_preserves_main_wal_and_sidecars(unsupported_wal):
    fake, target, shown, files, before = unsupported_wal
    result = fake.run("--db", shown)
    assert (result.returncode, result.stdout, result.stderr) == (
        1, "", f"sparks: {shown}: unsupported schema_version 2 (expected 1)\n",
    )
    fake.assert_calls()
    assert all(path.is_file() for path in files)
    assert {path: path.read_bytes() for path in files[:2]} == before
    # SHM read/lock state is ephemeral even with a read-only connection;
    # its existence, not byte equality, is part of this regression.
    with snapshot_reader(target) as db:
        assert db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == "2"
        assert tuple(db.execute("SELECT * FROM future_inventory").fetchone()) == (
            "opaque-id", "committed future data",
        )


def test_herdr_meta_without_schema_version_is_rejected_unchanged(fake_herdr):
    with contextlib.closing(sqlite3.connect(fake_herdr.db)) as db:
        db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("INSERT INTO meta VALUES ('future-key', 'keep this value')")
        db.commit()
    before = fake_herdr.db.read_bytes(), database_dump(fake_herdr.db)
    result = fake_herdr.run()
    assert (result.returncode, result.stdout, result.stderr) == (
        1, "", f"sparks: {fake_herdr.db}: unsupported schema_version None (expected 1)\n",
    )
    fake_herdr.assert_calls()
    assert_snapshot_unchanged(fake_herdr, before)


@pytest.mark.parametrize("kind", ["parent-file", "target-directory", "target-fifo"])
def test_herdr_non_directory_parent_or_nonregular_target_is_not_clobbered(fake_herdr, kind):
    target = fake_herdr.db
    if kind == "parent-file":
        parent = fake_herdr.directory / "parent-file"
        parent.write_bytes(b"keep parent bytes")
        target = parent / "state.sqlite"
    elif kind == "target-directory":
        target.mkdir()
    else:
        os.mkfifo(target)
    assert_rejected(fake_herdr.run("--db", str(target)), f"{target}: ")
    if kind == "parent-file":
        assert parent.read_bytes() == b"keep parent bytes"
    elif kind == "target-directory":
        assert target.is_dir() and list(target.iterdir()) == []
    else:
        assert stat.S_ISFIFO(target.stat().st_mode)


def test_herdr_sqlite_failure_rolls_back_updates_deletes_and_snapshot(saved_snapshot):
    fake, _ = saved_snapshot
    with contextlib.closing(sqlite3.connect(fake.db)) as db:
        db.execute("""CREATE TRIGGER fail_new_agent BEFORE INSERT ON agents
                      WHEN NEW.name = 'new-agent'
                      BEGIN SELECT RAISE(ABORT, 'simulated sqlite write failure'); END""")
        db.commit()
    before = database_dump(fake.db)
    fake.respond(changed_herdr_rows(fake.rows))
    assert_rejected(fake.run(), f"{fake.db}: simulated sqlite write failure")
    assert database_dump(fake.db) == before
    fake.assert_calls()
    # Rollback also releases the writer, so a later valid snapshot can commit.
    with contextlib.closing(sqlite3.connect(fake.db)) as db:
        db.execute("DROP TRIGGER fail_new_agent")
        db.commit()
    fake.clear_calls()
    assert_snapshot_success(fake, fake.run())
    fake.assert_calls()


def test_herdr_schema_and_meta_creation_roll_back_with_first_snapshot(fake_herdr):
    with contextlib.closing(sqlite3.connect(fake_herdr.db)) as db:
        db.execute("""CREATE TABLE workspaces (
            workspace_id TEXT PRIMARY KEY, label TEXT, number INTEGER, active_tab_id TEXT,
            agent_status TEXT, focused INTEGER, pane_count INTEGER, tab_count INTEGER,
            raw_json TEXT NOT NULL)""")
        db.execute("""CREATE TRIGGER fail_workspace BEFORE INSERT ON workspaces
                      BEGIN SELECT RAISE(ABORT, 'simulated first snapshot failure'); END""")
        db.commit()
    before = database_dump(fake_herdr.db)
    assert_rejected(fake_herdr.run(), f"{fake_herdr.db}: simulated first snapshot failure")
    assert database_dump(fake_herdr.db) == before  # no committed schema/meta without a snapshot
    fake_herdr.assert_calls()


@pytest.mark.parametrize("failure", ["rollback", "close"])
def test_herdr_sqlite_cleanup_errors_are_mapped_without_a_traceback(
    saved_snapshot, monkeypatch, capsys, failure,
):
    fake, before = saved_snapshot
    fake.respond(changed_herdr_rows(fake.rows))
    real_connect = sqlite3.connect

    class CleanupFailureConnection(sqlite3.Connection):
        def __exit__(self, exc_type, exc_value, traceback):
            if failure == "rollback" and exc_type is not None:
                # Even if explicit rollback fails, closing must release the
                # uncommitted transaction and the CLI must map the SQLite error.
                raise sqlite3.OperationalError("simulated sqlite rollback failure")
            return super().__exit__(exc_type, exc_value, traceback)

        def close(self):
            super().close()
            if failure == "close":
                raise sqlite3.OperationalError("simulated sqlite close failure")

    def fail_cleanup_connect(*args, **kwargs):
        if kwargs.get("uri") and "mode=ro" in str(args[0]).partition("?")[2].split("&"):
            return real_connect(*args, **kwargs)
        kwargs["factory"] = CleanupFailureConnection
        db = real_connect(*args, **kwargs)
        # Fail the final snapshot insert, after inventory upserts/deletes but
        # before commit. This tests close-error mapping without a committed write.
        db.set_authorizer(lambda action, table, *rest: (
            sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_INSERT and table == "snapshot"
            else sqlite3.SQLITE_OK
        ))
        return db

    with monkeypatch.context() as patch:
        patch.setattr(sqlite3, "connect", fail_cleanup_connect)
        code = cli.main(["herdr", "snapshot"])
    output = capsys.readouterr()
    result = subprocess.CompletedProcess([], code, output.out, output.err)
    assert_rejected(result, f"{fake.db}: simulated sqlite {failure} failure")
    fake.assert_calls()
    assert_snapshot_unchanged(fake, before)


def test_herdr_close_after_success_keeps_committed_result(saved_snapshot, monkeypatch, capsys):
    fake, _ = saved_snapshot
    with snapshot_reader(fake.db) as db:
        old_time = db.execute("SELECT captured_at FROM snapshot").fetchone()[0]
    fake.respond(changed_herdr_rows(fake.rows))
    real_connect = sqlite3.connect
    close_states = []

    class CloseAfterCommitFailureConnection(sqlite3.Connection):
        def close(self):
            close_states.append(self.in_transaction)
            super().close()
            raise sqlite3.OperationalError("simulated sqlite close failure after commit")

    def fail_close_connect(*args, **kwargs):
        if kwargs.get("uri") and "mode=ro" in str(args[0]).partition("?")[2].split("&"):
            return real_connect(*args, **kwargs)
        kwargs["factory"] = CloseAfterCommitFailureConnection
        return real_connect(*args, **kwargs)  # no authorizer: the final insert must commit

    time.sleep(0.01)
    started = datetime.now(timezone.utc)
    with monkeypatch.context() as patch:
        patch.setattr(sqlite3, "connect", fail_close_connect)
        code = cli.main(["herdr", "snapshot"])
    finished = datetime.now(timezone.utc)
    output = capsys.readouterr()
    result = subprocess.CompletedProcess([], code, output.out, output.err)
    assert close_states == [False]
    snapshot = assert_snapshot_success(fake, result)
    fake.assert_calls()
    assert snapshot["captured_at"] > old_time
    captured = datetime.fromisoformat(snapshot["captured_at"])
    assert started.timestamp() - 0.001 <= captured.timestamp() <= finished.timestamp()
    assert [snapshot[group + "_count"] for group in HERDR_GROUPS] == [2, 2, 3, 2]
    with snapshot_reader(fake.db) as db:
        assert db.execute("SELECT agent_status FROM agents WHERE name='state-review'").fetchone()[0] == "blocked"
        assert db.execute("SELECT agent_status FROM agents WHERE name='new-agent'").fetchone()[0] == "working"
        for table in HERDR_TABLES:
            assert db.execute(f"SELECT COUNT(*) FROM {table} WHERE workspace_id='w1'").fetchone()[0] == 0


def test_herdr_delete_database_lock_released_before_deadline_succeeds(delete_snapshot):
    fake, before = delete_snapshot
    with contextlib.closing(sqlite3.connect(fake.db)) as lock:
        lock.execute("BEGIN IMMEDIATE")
        started = time.monotonic()
        child = subprocess.Popen(
            [sys.executable, str(BIN), "herdr", "snapshot"], cwd=fake.directory,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8",
        )
        try:
            with pytest.raises(subprocess.TimeoutExpired):
                child.wait(timeout=1.25)
            fake.assert_calls()
            assert database_dump(fake.db) == before
            assert 1.0 <= time.monotonic() - started < 4.5
            lock.rollback()
            stdout, stderr = child.communicate(timeout=10)
            result = subprocess.CompletedProcess(child.args, child.returncode, stdout, stderr)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
    assert_snapshot_success(fake, result)
    fake.assert_calls()


def test_herdr_delete_database_held_lock_waits_then_preserves_logical_snapshot(delete_snapshot):
    fake, before = delete_snapshot
    with contextlib.closing(sqlite3.connect(fake.db)) as lock:
        lock.execute("BEGIN IMMEDIATE")
        started = time.monotonic()
        result = fake.run(timeout=12)
        elapsed = time.monotonic() - started
        assert (result.returncode, result.stdout, result.stderr) == (
            1, "", f"sparks: {fake.db}: database is locked\n",
        )
        assert 4.5 <= elapsed < 8
        assert database_dump(fake.db) == before
        lock.rollback()
    assert database_dump(fake.db) == before
    fake.assert_calls()


def test_herdr_locked_database_waits_then_keeps_previous_snapshot(saved_snapshot):
    fake, before = saved_snapshot
    fake.respond(changed_herdr_rows(fake.rows))
    with contextlib.closing(sqlite3.connect(fake.db)) as lock:
        lock.execute("BEGIN IMMEDIATE")
        started = time.monotonic()
        result = fake.run(timeout=12)
        elapsed = time.monotonic() - started
        assert_rejected(result, f"{fake.db}: database is locked")
        assert 4.5 <= elapsed < 12
        assert_snapshot_unchanged(fake, before)
        lock.rollback()
    fake.assert_calls()


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("group", ["workspace", "pane"])
def test_herdr_timeout_stops_calls_and_never_writes(fake_herdr, existing, group):
    before = fake_herdr.seed() if existing else None
    fake_herdr.monkeypatch.setenv("SPARKS_HERDR_TIMEOUT", "0.2")
    fake_herdr.respond(**{group: {"sleep": 2}})
    started = time.monotonic()
    result = fake_herdr.run(timeout=8)
    assert time.monotonic() - started < 8
    assert_rejected(result, "timed out")
    assert f"herdr {group} list" in result.stderr
    fake_herdr.assert_calls(HERDR_GROUPS[:HERDR_GROUPS.index(group) + 1])
    assert_snapshot_unchanged(fake_herdr, before)


@pytest.mark.parametrize("value", ["", "0", "-1", "nan", "NaN", "inf", "-inf", "1e999", "wrong"])
def test_herdr_bad_timeout_is_usage_error_before_any_calls(saved_snapshot, value):
    fake, before = saved_snapshot
    fake.monkeypatch.setenv("SPARKS_HERDR_TIMEOUT", value)
    result = fake.run()
    assert_rejected(result, "SPARKS_HERDR_TIMEOUT", code=2)
    fake.assert_calls(())
    assert_snapshot_unchanged(fake, before)


@pytest.mark.parametrize("value", [None, "1.25"])
def test_herdr_per_call_timeout_and_shell_false(fake_herdr, monkeypatch, capsys, value):
    if value is not None:
        monkeypatch.setenv("SPARKS_HERDR_TIMEOUT", value)
    real_run = subprocess.run
    calls = []

    def record_run(argv, *args, **kwargs):
        calls.append((argv, kwargs.get("timeout"), kwargs.get("shell", False)))
        return real_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", record_run)
    code = cli.main(["herdr", "snapshot"])
    output = capsys.readouterr()
    assert_snapshot_success(fake_herdr, subprocess.CompletedProcess([], code, output.out, output.err))
    assert calls == [
        ([str(fake_herdr.executable), group, "list"], 30 if value is None else 1.25, False)
        for group in HERDR_GROUPS
    ]
    fake_herdr.assert_calls()


@pytest.mark.parametrize("herdr_env", [None, "0", "1"])
def test_herdr_socket_and_env_are_preserved_without_requiring_pane_env(fake_herdr, herdr_env):
    if herdr_env is not None:
        fake_herdr.monkeypatch.setenv("HERDR_ENV", herdr_env)
    assert_snapshot_success(fake_herdr, fake_herdr.run())
    fake_herdr.assert_calls()
    assert all(call["socket"] == "/tmp/test-herdr.sock" for call in fake_herdr.calls)
    assert all(call["herdr_env"] == herdr_env for call in fake_herdr.calls)


def test_herdr_execution_oserror_is_one_line_and_writes_nothing(fake_herdr, monkeypatch, capsys):
    calls = []

    def deny_execution(argv, *args, **kwargs):
        calls.append(argv)
        raise PermissionError(errno.EACCES, os.strerror(errno.EACCES))

    monkeypatch.setattr(subprocess, "run", deny_execution)
    assert cli.main(["herdr", "snapshot"]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == f"sparks: herdr: {os.strerror(errno.EACCES)}\n"
    assert calls == [[str(fake_herdr.executable), "workspace", "list"]]
    assert not fake_herdr.db.exists()
    fake_herdr.assert_calls(())  # it was resolved, but never executed


def test_herdr_bad_utf8_stdout_uses_replacement_not_a_traceback(fake_herdr):
    rows = herdr_rows()
    rows["workspaces"][0]["label"] = "invalid byte: BYTE"
    frame = {"result": {"type": "workspace_list", "workspaces": rows["workspaces"]}}
    raw = json.dumps(frame, ensure_ascii=False).encode().replace(b"BYTE", b"\xff")
    rows["workspaces"][0]["label"] = "invalid byte: �"
    fake_herdr.respond(rows, workspace={"stdout_hex": raw.hex()})
    assert_snapshot_success(fake_herdr, fake_herdr.run())
    fake_herdr.assert_calls()


def test_herdr_bad_utf8_stderr_is_replaced_and_clipped_to_one_line(saved_snapshot):
    fake, before = saved_snapshot
    reason = b"invalid byte: \xff\r\n" + b"long reason " * 200
    fake.respond(pane={"stdout": "", "stderr_hex": reason.hex(), "code": 2})
    result = fake.run()
    assert_rejected(result, "herdr pane list: ")
    assert "�" in result.stderr
    assert len(result.stderr) <= 600
    fake.assert_calls(("workspace", "tab", "pane"))
    assert_snapshot_unchanged(fake, before)


def test_herdr_in_process_closed_stdout_stream_still_commits(fake_herdr, monkeypatch, capsys):
    closed = io.StringIO()
    closed.close()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", closed)
        code = cli.main(["herdr", "snapshot"])
    output = capsys.readouterr()
    assert code == 0
    assert (output.out, output.err) == ("", "")
    assert_snapshot_entities(fake_herdr.db, fake_herdr.rows)
    fake_herdr.assert_calls()


@posix
@pytest.mark.parametrize("kind", ["closed", "broken-pipe"])
def test_herdr_closed_or_broken_stdout_still_commits(fake_herdr, kind):
    kwargs = {}
    write_end = None
    if kind == "closed":
        kwargs["preexec_fn"] = lambda: os.close(1)
    else:
        read_end, write_end = os.pipe()
        os.close(read_end)
        kwargs["stdout"] = write_end
    try:
        result = subprocess.run(
            [sys.executable, str(BIN), "herdr", "snapshot"], cwd=fake_herdr.directory,
            stderr=subprocess.PIPE, encoding="utf-8", timeout=15, **kwargs,
        )
    finally:
        if write_end is not None:
            os.close(write_end)
    assert (result.returncode, result.stderr) == (0, "")
    assert_snapshot_entities(fake_herdr.db, fake_herdr.rows)
    fake_herdr.assert_calls()


@pytest.mark.parametrize("kind", ["newline", "non-ascii"])
def test_herdr_database_output_uses_sparks_add_path_escaping(fake_herdr, kind):
    name = "two\nlines.sqlite" if kind == "newline" else "café.sqlite"
    target = fake_herdr.directory / name
    env = {} if kind == "newline" else {"PYTHONIOENCODING": "ascii:strict"}
    result = fake_herdr.run("--db", str(target), env=env)
    shown = repr(str(target)) if kind == "newline" else str(target).encode("ascii", "backslashreplace").decode("ascii")
    assert_snapshot_success(fake_herdr, result, db=target, shown_db=shown)
    fake_herdr.assert_calls()


def test_herdr_snapshot_help_is_noninteractive_and_keeps_sparks_add_help(fake_herdr):
    result = sparks("herdr", "snapshot", "--help", cwd=fake_herdr.directory)
    assert (result.returncode, result.stderr) == (0, "")
    text = " ".join(result.stdout.split())
    for group in HERDR_GROUPS:
        assert f"herdr {group} list" in text
    assert "SQLite" in text
    assert "bare" in text and "herdr" in text and "never" in text.lower()
    assert "missing" in text and "not running" in text and "nonzero" in text
    spark_help = sparks("add", "--help", cwd=fake_herdr.directory)
    assert spark_help.returncode == 0
    assert spark_help.stdout.startswith("usage: sparks add [-h] [--path <path>] --json <json>\n")
    fake_herdr.assert_calls(())
    assert not fake_herdr.db.exists()


@pytest.mark.parametrize("args", [
    ["herdr"], ["herdr", "unknown"], ["herdr", "snapshot", "--unknown"],
    ["herdr", "snapshot", "extra"], ["herdr", "snapshot", "--db"],
])
def test_herdr_usage_errors_do_not_call_herdr_or_write(fake_herdr, args):
    result = sparks(*args, cwd=fake_herdr.directory)
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("usage: sparks")
    fake_herdr.assert_calls(())
    assert not fake_herdr.db.exists()


def test_herdr_snapshot_public_files_and_fixtures_have_no_machine_specific_strings():
    # Assemble prohibited spellings so the guard itself is not a fixture violation.
    forbidden = (
        "/home/" + "box", "/" + "workspace", "Arch" + "Agents", "God" + "dy",
        "Grok" + " Bot", "Grok" + "box",
    )
    public_files = (
        BIN, ROOT / "README.md", ROOT / "CHANGELOG.md",
        ROOT / "skills" / "herdr-operations" / "SKILL.md",
        ROOT / "skills" / "herdr-operations" / "scripts" / "README.md",
    )
    for path in public_files:
        text = path.read_text(encoding="utf-8")
        for value in forbidden:
            assert value not in text, (path.relative_to(ROOT), value)
    for value in forbidden:
        assert value not in Path(__file__).read_text(encoding="utf-8")
        assert value not in json.dumps(herdr_rows(), ensure_ascii=False)

# format and ids


def test_schema_describes_a_list_of_sparks_without_changing_its_shape():
    schema = json.loads((ROOT / "sparks.schema.json").read_bytes())
    assert schema["title"] == "List of sparks"
    assert "list of sparks" in schema["description"]
    assert "One spark:" in schema["$defs"]["spark"]["description"]
    assert schema["$id"].endswith("/sparks.schema.json")
    validator = Draft202012Validator(schema)
    validator.validate([])
    validator.validate([FIRST, stored(SECOND)])
    assert not validator.is_valid(FIRST)


@pytest.mark.parametrize("invalid", [1, {}, {"type": "s", "question": "q"}])
def test_load_shape_diagnostic_calls_the_primitive_a_spark(tmp_path, invalid):
    path = tmp_path / "sparks.json"
    path.write_text(json.dumps([invalid]), encoding="utf-8")
    with pytest.raises(spark_id_mod.SparkFileError, match="each spark must be an object"):
        spark_id_mod.load(path)


def test_add_writes_the_xxh64_id_and_prints_it(tmp_path):
    path = tmp_path / "sparks.json"
    result = add(path, FIRST)
    (written,) = json.loads(path.read_bytes())
    preimage = json.dumps(
        {"answer": FIRST["answer"], "question": FIRST["question"], "type": "s"},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    assert written["id"] == spark_hash.xxh64_hexdigest(preimage)
    assert result.stdout == f"added {written['id']} to {path}\n"
    assert list(written) == ["type", "question", "answer", "id"]


def test_file_without_ids_stays_valid_and_add_backfills_the_matched_id(tmp_path):
    path = tmp_path / "sparks.json"
    before = seed(path, [FIRST, SECOND])
    assert spark_id_mod.main(["spark_id.py", str(path)]) == 0
    assert add(path, SECOND).returncode == 0
    sparks = json.loads(path.read_bytes())
    assert sparks == [FIRST, stored(SECOND)]
    assert before != path.read_bytes()


def test_replacement_keeps_a_stored_id(tmp_path):
    path = tmp_path / "sparks.json"
    seed(path, [stored(FIRST)])
    revised = spark(FIRST["question"], "Updated.")
    result = add(path, revised)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"added {spark_id(FIRST)} to {path}\n"
    assert json.loads(path.read_bytes()) == [{**revised, "id": spark_id(FIRST)}]


def test_stored_id_is_not_recomputed_on_load(tmp_path):
    path = tmp_path / "sparks.json"
    seed(path, [{**FIRST, "id": "0123456789abcdef"}])
    (loaded,) = spark_id_mod.load(path)
    assert loaded.id == "0123456789abcdef"


def test_duplicate_stored_ids_are_refused(tmp_path):
    path = tmp_path / "sparks.json"
    seed(path, [{**FIRST, "id": "0" * 16}, {**SECOND, "id": "0" * 16}])
    with pytest.raises(spark_id_mod.SparkFileError, match="duplicate id"):
        spark_id_mod.load(path)


def test_example_id_is_pinned():
    for spark in json.loads((ROOT / "sparks.json").read_bytes()):
        assert spark["id"] == spark_id({k: spark[k] for k in ("type", "question", "answer")})


def test_hash_script_has_no_dependencies():
    text = (ROOT / "spark_hash.py").read_text(encoding="utf-8")
    assert "# dependencies = []" in text
    imports = {line.split()[1].split(".")[0] for line in text.splitlines()
               if line.startswith(("import ", "from "))}
    assert imports <= {"struct", "sys", "__future__"}, imports



def test_load_does_not_rehash_a_stored_id(tmp_path, monkeypatch):
    path = tmp_path / "sparks.json"
    expected = spark_id(FIRST)
    seed(path, [stored(FIRST)])

    def fail(*args):
        raise AssertionError("derive_id called for a stored id")

    monkeypatch.setattr(spark_id_mod, "derive_id", fail)
    assert spark_id_mod.load(path)[0].id == expected


@pytest.mark.parametrize("bad", [None, 1, "0123456789abcdef\n", "0" * 17])
def test_load_refuses_a_malformed_stored_id(tmp_path, bad):
    path = tmp_path / "sparks.json"
    seed(path, [{**FIRST, "id": bad}])
    with pytest.raises(spark_id_mod.SparkFileError, match="id must be"):
        spark_id_mod.load(path)
    schema = json.loads((ROOT / "sparks.schema.json").read_bytes())
    assert not Draft202012Validator(schema).is_valid([{**FIRST, "id": bad}])


def test_connect_refuses_a_type_only_change_under_one_id():
    old = spark_id_mod.Spark(FIRST["question"], FIRST["answer"], "S", "0" * 16)
    new = spark_id_mod.Spark(FIRST["question"], FIRST["answer"], "R", "0" * 16)
    with pytest.raises(spark_id_mod.SparkFileError, match="type"):
        spark_id_mod.connect([old], [new])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-p", "no:cacheprovider", *sys.argv[1:]]))

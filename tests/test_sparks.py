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
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

INSTALLED_PI_DIR = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi" / "agent"))
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



@pytest.mark.parametrize("spark_type", ["S", "R", "k", "K"])
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


@pytest.mark.parametrize(("table", "field"), [
    ("workspaces", "workspace_id"), ("tabs", "tab_id"), ("tabs", "workspace_id"),
    ("panes", "pane_id"), ("panes", "workspace_id"), ("panes", "tab_id"),
    ("agents", "name"), ("agents", "pane_id"), ("agents", "workspace_id"), ("agents", "tab_id"),
])
@pytest.mark.parametrize("value", [DROP, None, "", 1, False], ids=["missing", "null", "empty", "int", "bool"])
def test_herdr_all_identity_fields_are_required_nonempty_strings(saved_snapshot, table, field, value):
    if (table, field) == ("agents", "name") and value in (DROP, None, ""):
        pytest.skip("an unnamed agent is skipped, not rejected: see the unnamed-agent tests")
    fake, before = saved_snapshot
    rows = herdr_rows()
    if value is DROP:
        rows[table][0].pop(field)
    else:
        rows[table][0][field] = value
    fake.respond(rows)
    assert_invalid_herdr_rows(fake, table, before)


def unnamed_agent_rows(name):
    """Fixture rows plus a third agent, and its pane, that herdr reports without a name."""
    rows = herdr_rows()
    pane = {**copy.deepcopy(rows["panes"][0]), "pane_id": "w3:pU", "terminal_id": "term_u"}
    agent = {**copy.deepcopy(rows["agents"][0]), "pane_id": "w3:pU", "terminal_id": "term_u"}
    if name is DROP:
        del agent["name"]
    else:
        agent["name"] = name
    rows["panes"].append(pane)
    rows["agents"].append(agent)
    return rows


@pytest.mark.parametrize("name", [DROP, None, ""], ids=["missing", "null", "empty"])
@pytest.mark.parametrize("existing", [False, True])
def test_herdr_unnamed_agent_is_skipped_with_a_warning_not_a_failed_snapshot(fake_herdr, existing, name):
    # herdr 0.9.5 lists an agent with no name key; that row once aborted the whole snapshot.
    if existing:
        fake_herdr.seed()
    rows = unnamed_agent_rows(name)
    fake_herdr.respond(rows)
    result = fake_herdr.run()
    assert result.returncode == 0, result.stderr
    assert result.stderr == "sparks: warning: herdr agent list: agents[2]: no name, not stored (pane w3:pU)\n"
    stored = {**rows, "agents": rows["agents"][:2]}
    snapshot = assert_snapshot_entities(fake_herdr.db, stored)
    assert result.stdout == (
        f"snapshot {snapshot['captured_at']} workspaces=3 tabs=4 panes=5 agents=2 db={fake_herdr.db}\n"
    )
    fake_herdr.assert_calls()


def test_herdr_agent_that_loses_its_name_is_pruned(saved_snapshot):
    fake, _ = saved_snapshot
    rows = herdr_rows()
    del rows["agents"][0]["name"]
    fake.respond(rows)
    result = fake.run()
    assert result.returncode == 0, result.stderr
    assert result.stderr == "sparks: warning: herdr agent list: agents[0]: no name, not stored (pane w3:pX)\n"
    assert_snapshot_entities(fake.db, {**rows, "agents": rows["agents"][1:]})


@pytest.mark.parametrize(("field", "value"), [("pane_id", DROP), ("tab_id", ""), ("revision", "2")])
def test_herdr_unnamed_agent_row_is_still_validated(saved_snapshot, field, value):
    fake, before = saved_snapshot
    rows = unnamed_agent_rows(DROP)
    if value is DROP:
        del rows["agents"][2][field]
    else:
        rows["agents"][2][field] = value
    fake.respond(rows)
    assert_invalid_herdr_rows(fake, "agents", before)


def test_herdr_unnamed_agent_cannot_share_a_named_agents_pane(saved_snapshot):
    fake, before = saved_snapshot
    rows = unnamed_agent_rows(DROP)
    rows["agents"][2]["pane_id"] = rows["agents"][0]["pane_id"]
    fake.respond(rows)
    assert_invalid_herdr_rows(fake, "agents", before)


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
    ["herdr", "query", "nope"], ["herdr", "query", "--db"],
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
        ROOT / "defaults" / "agent.toml", ROOT / "skills" / "agent-personas" / "SKILL.md",
    )
    for path in public_files:
        text = path.read_text(encoding="utf-8")
        for value in forbidden:
            assert value not in text, (path.relative_to(ROOT), value)
    for value in forbidden:
        assert value not in Path(__file__).read_text(encoding="utf-8")
        assert value not in json.dumps(herdr_rows(), ensure_ascii=False)


def captured_at(path):
    with snapshot_reader(path) as db:
        return db.execute("SELECT captured_at FROM snapshot").fetchone()[0]


def query_sparks(fake, *args):
    return sparks("herdr", "query", *args, cwd=fake.directory)


def test_herdr_query_summary_hides_done_and_keeps_short_columns(saved_snapshot):
    fake, before = saved_snapshot
    result = query_sparks(fake)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    stamp = captured_at(fake.db)
    assert result.stdout == (
        f"snapshot {stamp} workspaces=3 tabs=4 panes=4 agents=2 db={fake.db}\n"
        "agents blocked=0 idle=0 working=1 unknown=0 done=1\n"
        "status\tname\tkind\tws\tpane\tcwd\n"
        "working\tstate-review\tpi\tw3\tw3:pX\t/tmp/proj\n"
    )
    assert "completed-task" not in result.stdout
    assert "session.jsonl" not in result.stdout
    assert "term_" not in result.stdout
    assert "04ede96e" not in result.stdout
    fake.assert_calls(())
    assert_snapshot_unchanged(fake, before)


def test_herdr_query_agents_lists_done_and_sorts_status_then_name(saved_snapshot):
    fake, before = saved_snapshot
    result = query_sparks(fake, "agents")
    stamp = captured_at(fake.db)
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        f"snapshot {stamp} agents=2 db={fake.db}\n"
        "status\tname\tkind\tws\tpane\tcwd\n"
        "working\tstate-review\tpi\tw3\tw3:pX\t/tmp/proj\n"
        "done\tcompleted-task\tclaude\tw1\tw1:pC\t/tmp/proj\n"
    )
    assert_snapshot_unchanged(fake, before)
    fake.assert_calls(())


def test_herdr_query_workspaces_tabs_and_panes_project_parsed_fields(saved_snapshot):
    fake, _before = saved_snapshot
    stamp = captured_at(fake.db)
    workspaces = query_sparks(fake, "workspaces")
    assert workspaces.stdout == (
        f"snapshot {stamp} workspaces=3 db={fake.db}\n"
        "id\tn\tstatus\ttabs\tpanes\tfocus\tactive\tlabel\n"
        "w3\t3\tdone\t13\t13\t0\tw3:tX\tsparks\n"
        "w1\t6\tdone\t2\t2\t1\tw1:tB\ttasks\n"
        "w6\t7\tunknown\t1\t1\t0\tw6:t1\trestored\n"
    )
    tabs = query_sparks(fake, "tabs")
    assert tabs.stdout == (
        f"snapshot {stamp} tabs=4 db={fake.db}\n"
        "id\tws\tn\tstatus\tpanes\tfocus\tlabel\n"
        "w1:tB\tw1\t1\tdone\t1\t0\tcompleted-task\n"
        "w1:t1\tw1\t2\tunknown\t1\t1\tshell\n"
        "w3:tX\tw3\t29\tworking\t1\t0\tstate-review\n"
        "w6:t1\tw6\t1\tunknown\t1\t0\trestored\n"
    )
    panes = query_sparks(fake, "panes")
    assert panes.stdout == (
        f"snapshot {stamp} panes=4 db={fake.db}\n"
        "id\tws\ttab\tstatus\tkind\tname\tcwd\trestore\n"
        "w1:p1\tw1\tw1:t1\tunknown\t\t\t/tmp/proj\t\n"
        "w1:pC\tw1\tw1:tB\tdone\tclaude\tcompleted-task\t/tmp/proj\t\n"
        "w3:pX\tw3\tw3:tX\tworking\tpi\tstate-review\t/tmp/proj\t\n"
        "w6:p1\tw6\tw6:t1\tunknown\t\t\t/tmp/proj\tSaved directory is unavailable.\n"
    )
    assert "spark id hashing" not in panes.stdout
    assert "\u03c0" not in panes.stdout
    fake.assert_calls(())


def test_herdr_query_raw_prints_the_stored_fetch_object(saved_snapshot):
    fake, before = saved_snapshot
    with snapshot_reader(fake.db) as db:
        stored = db.execute("SELECT raw_json FROM agents WHERE name = 'state-review'").fetchone()[0]
    result = query_sparks(fake, "agents", "--name", "state-review", "--raw")
    stamp = captured_at(fake.db)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"snapshot {stamp} agents=1 of=2 db={fake.db}\n{stored}\n"
    assert json.loads(stored)["name"] == "state-review"
    assert "agent_session" in stored
    assert_snapshot_unchanged(fake, before)


def test_herdr_query_filters_are_exact_and_zero_matches_succeed(saved_snapshot):
    fake, before = saved_snapshot
    stamp = captured_at(fake.db)
    working = query_sparks(fake, "agents", "--workspace", "w1", "--status", "done")
    assert working.returncode == 0, working.stderr
    assert "completed-task" in working.stdout
    assert "state-review" not in working.stdout
    assert working.stdout.startswith(f"snapshot {stamp} agents=1 of=2 db={fake.db}\n")
    summary = query_sparks(fake, "--status", "done")
    assert summary.returncode == 0, summary.stderr
    assert f"agents=2 matched=1 db={fake.db}" in summary.stdout
    assert "done=1" in summary.stdout
    assert "completed-task" not in summary.stdout
    empty = query_sparks(fake, "agents", "--name", "missing")
    assert empty.returncode == 0, empty.stderr
    assert empty.stdout == (
        f"snapshot {stamp} agents=0 of=2 db={fake.db}\n"
        "status\tname\tkind\tws\tpane\tcwd\n"
    )
    panes = query_sparks(fake, "panes", "--name", "state-review")
    assert panes.returncode == 0, panes.stderr
    assert "w3:pX" in panes.stdout and "w1:p1" not in panes.stdout
    assert_snapshot_unchanged(fake, before)
    fake.assert_calls(())


@pytest.mark.parametrize(("args", "message"), [
    (["workspaces", "--name", "state-review"], "--name does not apply to workspaces"),
    (["tabs", "--name", "state-review"], "--name does not apply to tabs"),
    (["workspaces", "--tab", "w3:tX"], "--tab does not apply to workspaces"),
    (["--raw"], "--raw does not apply to summary"),
    (["summary", "--raw"], "--raw does not apply to summary"),
])
def test_herdr_query_inapplicable_filters_are_usage_errors(saved_snapshot, args, message):
    fake, before = saved_snapshot
    result = query_sparks(fake, *args)
    assert_rejected(result, message, code=2)
    fake.assert_calls(())
    assert_snapshot_unchanged(fake, before)


def test_herdr_query_collapses_whitespace_and_quotes_odd_status_counts(fake_herdr):
    rows = herdr_rows()
    rows["agents"][0]["cwd"] = "a\nb\tc"
    rows["agents"][0]["agent_status"] = "future status"
    rows["workspaces"][0]["label"] = "\u03c0 spark"
    fake_herdr.respond(rows)
    assert fake_herdr.run().returncode == 0
    fake_herdr.clear_calls()
    agents = query_sparks(fake_herdr, "agents", "--status", "future status")
    assert agents.returncode == 0, agents.stderr
    assert "working" not in agents.stdout.splitlines()[-1]
    assert agents.stdout.endswith("future status\tstate-review\tpi\tw3\tw3:pX\ta b c\n")
    summary = query_sparks(fake_herdr)
    assert '"future status"=1' in summary.stdout
    assert "\u03c0 spark" in query_sparks(fake_herdr, "workspaces").stdout
    fake_herdr.assert_calls(())


def test_herdr_query_empty_inventory_is_a_header_only_table(fake_herdr):
    fake_herdr.respond({table: [] for table in HERDR_TABLES})
    assert fake_herdr.run().returncode == 0
    fake_herdr.clear_calls()
    result = query_sparks(fake_herdr)
    stamp = captured_at(fake_herdr.db)
    assert result.stdout == (
        f"snapshot {stamp} workspaces=0 tabs=0 panes=0 agents=0 db={fake_herdr.db}\n"
        "agents blocked=0 idle=0 working=0 unknown=0 done=0\n"
        "status\tname\tkind\tws\tpane\tcwd\n"
    )
    fake_herdr.assert_calls(())


def test_herdr_query_missing_database_creates_nothing(fake_herdr):
    target = fake_herdr.directory / "missing" / "nested" / "state.sqlite"
    result = query_sparks(fake_herdr, "--db", str(target))
    assert_rejected(result, "no snapshot")
    assert str(target) in result.stderr
    assert not target.parent.exists()
    assert not fake_herdr.db.exists()
    fake_herdr.assert_calls(())


def test_herdr_query_bad_timeout_does_not_matter(saved_snapshot):
    fake, before = saved_snapshot
    fake.monkeypatch.setenv("SPARKS_HERDR_TIMEOUT", "nope")
    result = query_sparks(fake, "agents")
    assert result.returncode == 0, result.stderr
    assert "state-review" in result.stdout
    fake.assert_calls(())
    assert_snapshot_unchanged(fake, before)


def test_herdr_query_unsupported_schema_and_count_mismatch_change_nothing(fake_herdr):
    fake_herdr.seed()
    fake_herdr.clear_calls()
    with contextlib.closing(sqlite3.connect(fake_herdr.db)) as db:
        db.execute("UPDATE meta SET value = '2' WHERE key = 'schema_version'")
        db.commit()
    refused = fake_herdr.db.read_bytes()
    result = query_sparks(fake_herdr)
    assert_rejected(result, "unsupported schema_version 2")
    assert fake_herdr.db.read_bytes() == refused
    with contextlib.closing(sqlite3.connect(fake_herdr.db)) as db:
        db.execute("UPDATE meta SET value = '1' WHERE key = 'schema_version'")
        db.execute("UPDATE snapshot SET agent_count = 0")
        db.commit()
    mismatched = database_dump(fake_herdr.db)
    result = query_sparks(fake_herdr)
    assert_rejected(result, "snapshot counts do not match inventory")
    assert database_dump(fake_herdr.db) == mismatched
    fake_herdr.assert_calls(())


def test_herdr_query_does_not_change_bytes_mtime_or_sidecars(saved_snapshot):
    fake, before = saved_snapshot
    sidecars = sorted(p.name for p in fake.db.parent.iterdir())
    mtime = fake.db.stat().st_mtime_ns
    result = query_sparks(fake, "panes")
    assert result.returncode == 0, result.stderr
    assert fake.db.read_bytes() == before[0]
    assert fake.db.stat().st_mtime_ns == mtime
    assert sorted(p.name for p in fake.db.parent.iterdir()) == sidecars
    fake.assert_calls(())


@pytest.mark.parametrize("choice", ["argument", "environment", "xdg", "empty-xdg", "default-missing"])
def test_herdr_query_path_precedence_does_not_create_a_default(fake_herdr, choice):
    fake = fake_herdr
    fake.seed()
    fake.clear_calls()
    if choice == "argument":
        explicit = fake.directory / "explicit.sqlite"
        explicit.write_bytes(fake.db.read_bytes())
        result = query_sparks(fake, "--db", str(explicit), "agents")
        assert result.returncode == 0, result.stderr
        assert f"db={explicit}" in result.stdout
    elif choice == "environment":
        result = query_sparks(fake, "summary")
        assert result.returncode == 0, result.stderr
        assert f"db={fake.db}" in result.stdout
    else:
        fake.monkeypatch.delenv("SPARKS_HERDR_DB")
        if choice == "xdg":
            expected = fake.xdg / "sparks" / "herdr-state.sqlite"
        else:
            if choice == "empty-xdg":
                fake.monkeypatch.setenv("XDG_DATA_HOME", "")
            else:
                fake.monkeypatch.delenv("XDG_DATA_HOME")
            expected = fake.home / ".local" / "share" / "sparks" / "herdr-state.sqlite"
        result = query_sparks(fake)
        assert_rejected(result, "no snapshot")
        assert str(expected) in result.stderr
        assert not expected.parent.exists()
    fake.assert_calls(())


def test_herdr_query_relative_path_spelling_is_not_resolved(fake_herdr):
    shown = "./relative.sqlite"
    assert fake_herdr.run("--db", shown).returncode == 0
    fake_herdr.clear_calls()
    result = sparks("herdr", "query", "--db", shown, "agents", cwd=fake_herdr.directory)
    assert result.returncode == 0, result.stderr
    assert f"db={shown}" in result.stdout
    assert str((fake_herdr.directory / "relative.sqlite").resolve()) not in result.stdout
    fake_herdr.assert_calls(())


def test_herdr_query_help_is_noninteractive(fake_herdr):
    result = sparks("herdr", "query", "--help", cwd=fake_herdr.directory)
    assert result.returncode == 0, result.stderr
    text = " ".join(result.stdout.split())
    assert "Does not call herdr" in result.stdout
    assert "does not write" in text
    assert "tab-separated" in text
    assert "--raw" in result.stdout
    assert "summary" in result.stdout
    fake_herdr.assert_calls(())
    assert not fake_herdr.db.exists()


def test_herdr_query_help_mentions_command_on_herdr_help(tmp_path):
    result = sparks("herdr", "--help", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "query" in result.stdout
    assert "snapshot" in result.stdout


@pytest.mark.parametrize("status", [None, "", "DONE", "done ", "null"])
def test_herdr_query_summary_only_excludes_exact_done(fake_herdr, status):
    rows = herdr_rows()
    rows["agents"][0]["agent_status"] = status
    fake_herdr.respond(rows)
    assert fake_herdr.run().returncode == 0
    fake_herdr.clear_calls()
    result = query_sparks(fake_herdr, "--workspace", "w3")
    assert result.returncode == 0, result.stderr
    assert "state-review" in result.stdout
    assert "completed-task" not in result.stdout
    fake_herdr.assert_calls(())


def test_herdr_query_counts_do_not_merge_distinct_statuses(fake_herdr):
    rows = herdr_rows()
    statuses = [None, "null", "", "empty", "idle", " idle ", "future status", "future\tstatus"]
    template = rows["agents"][0]
    rows["agents"] = [
        {**template, "name": f"agent-{i}", "pane_id": f"pane-{i}", "agent_status": status}
        for i, status in enumerate(statuses)
    ]
    fake_herdr.respond(rows)
    assert fake_herdr.run().returncode == 0
    fake_herdr.clear_calls()
    result = query_sparks(fake_herdr)
    assert result.returncode == 0, result.stderr
    counts = result.stdout.splitlines()[1]
    for field in ('null=1', '"null"=1', '""=1', 'empty=1', 'idle=1', '" idle "=1',
                  '"future status"=1', '"future\\tstatus"=1'):
        assert field in counts
    fake_herdr.assert_calls(())


@pytest.mark.parametrize("view", ["summary", "agents", "workspaces", "tabs", "panes"])
def test_herdr_query_readonly_uri_never_creates_wal_sidecars(saved_snapshot, monkeypatch, view):
    fake, before = saved_snapshot
    # The fixture's diagnostic mode=ro reader can itself leave empty sidecars.
    # Remove those fixture artifacts so creation by the query cannot go unnoticed.
    wal = Path(str(fake.db) + "-wal")
    shm = Path(str(fake.db) + "-shm")
    assert not wal.exists() or wal.stat().st_size == 0
    wal.unlink(missing_ok=True)
    shm.unlink(missing_ok=True)
    # Catch transient sidecar creation, even if SQLite removes it on close.
    original_connect = cli.sqlite3.connect
    def connect(database, **kwargs):
        assert kwargs["uri"] is True
        assert database.endswith("?mode=ro&immutable=1")
        db = original_connect(database, **kwargs)
        assert not Path(str(fake.db) + "-wal").exists()
        assert not Path(str(fake.db) + "-shm").exists()
        return db
    monkeypatch.setattr(cli.sqlite3, "connect", connect)
    assert cli.main(["herdr", "query", view]) == 0
    assert not wal.exists() and not shm.exists()
    assert fake.db.read_bytes() == before[0]
    fake.assert_calls(())


@pytest.mark.parametrize("suffix", ["-wal", "-journal"])
def test_herdr_query_refuses_pending_journals_without_changes(saved_snapshot, suffix):
    fake, _ = saved_snapshot
    # A live connection keeps a real committed WAL, rather than just a dummy file.
    with contextlib.closing(sqlite3.connect(fake.db)) as writer:
        if suffix == "-wal":
            writer.execute("UPDATE agents SET agent_status='blocked' WHERE name='state-review'")
            writer.commit()
        else:
            assert writer.execute("PRAGMA journal_mode=DELETE").fetchone()[0] == "delete"
            writer.execute("UPDATE agents SET agent_status='blocked' WHERE name='state-review'")
        files = list(fake.directory.glob("state.sqlite*"))
        assert Path(str(fake.db) + suffix) in files
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files}
        result = query_sparks(fake)
        assert_rejected(result, "pending journal data")
        assert list(fake.directory.glob("state.sqlite*")) == files
        assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files} == before
    fake.assert_calls(())


def test_herdr_query_detects_concurrent_database_change(saved_snapshot, monkeypatch, capsys):
    fake, _ = saved_snapshot
    body = cli._query_body
    def changed(*args, **kwargs):
        result = body(*args, **kwargs)
        os.utime(fake.db, ns=(fake.db.stat().st_atime_ns, fake.db.stat().st_mtime_ns + 1_000_000))
        return result
    monkeypatch.setattr(cli, "_query_body", changed)
    assert cli.main(["herdr", "query"]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.count("\n") == 1
    assert "snapshot changed while reading" in output.err
    fake.assert_calls(())


@pytest.mark.parametrize("kind", ["corrupt", "directory", "dangling", "empty"])
def test_herdr_query_read_failures_are_one_line_and_create_nothing(fake_herdr, kind):
    fake = fake_herdr
    if kind == "directory":
        fake.db.mkdir()
    elif kind == "dangling":
        fake.db.symlink_to(fake.directory / "absent.sqlite")
    else:
        fake.db.write_bytes(b"not a database" if kind == "corrupt" else b"")
    files = sorted(p.name for p in fake.directory.iterdir())
    result = query_sparks(fake)
    assert_rejected(result, "sparks:")
    assert sorted(p.name for p in fake.directory.iterdir()) == files
    fake.assert_calls(())


@pytest.mark.parametrize("view", ["agents", "summary", "panes"])
def test_herdr_query_all_filters_combine_exactly(saved_snapshot, view):
    fake, _ = saved_snapshot
    args = (view, "--status", "working", "--workspace", "w3", "--tab", "w3:tX", "--name")
    result = query_sparks(fake, *args, "state-review")
    assert result.returncode == 0, result.stderr
    assert "state-review" in result.stdout
    assert "completed-task" not in result.stdout
    for name in ("state", "STATE-REVIEW", "state-review' OR 1=1 --"):
        empty = query_sparks(fake, *args, name)
        assert empty.returncode == 0, empty.stderr
        assert "state-review" not in empty.stdout
        assert "completed-task" not in empty.stdout
    fake.assert_calls(())


@pytest.mark.parametrize("choice", ["xdg", "home", "empty-xdg"])
def test_herdr_query_reads_default_path(fake_herdr, choice):
    fake = fake_herdr
    fake.monkeypatch.delenv("SPARKS_HERDR_DB")
    if choice == "xdg":
        expected = fake.xdg / "sparks" / "herdr-state.sqlite"
    else:
        if choice == "empty-xdg":
            fake.monkeypatch.setenv("XDG_DATA_HOME", "")
        else:
            fake.monkeypatch.delenv("XDG_DATA_HOME")
        expected = fake.home / ".local" / "share" / "sparks" / "herdr-state.sqlite"
    assert fake.run().returncode == 0
    fake.clear_calls()
    result = query_sparks(fake)
    assert result.returncode == 0, result.stderr
    assert f"db={expected}" in result.stdout
    fake.assert_calls(())


@pytest.mark.parametrize("name", ["query?mode=rw#%23.sqlite", "alias.sqlite"])
def test_herdr_query_uri_escaping_and_symlinks(saved_snapshot, name):
    fake, _ = saved_snapshot
    alias = fake.directory / name
    alias.symlink_to(fake.db)
    result = query_sparks(fake, "--db", str(alias), "agents")
    assert result.returncode == 0, result.stderr
    assert "state-review" in result.stdout
    # Journal checks must follow the same resolved target as SQLite.
    with contextlib.closing(sqlite3.connect(fake.db)) as writer:
        writer.execute("UPDATE agents SET agent_status='blocked'")
        writer.commit()
        result = query_sparks(fake, "--db", str(alias))
        assert_rejected(result, "pending journal data")
    fake.assert_calls(())


# agent spawn


PI_TABLE = """\
provider      model              context  max-out  thinking  images
anthropic     claude-opus-5      1M       128K     yes       yes
openai        gpt-4o             128K     16K      no        yes
openai        gpt-5.5            1M       128K     yes       yes
openai-codex  gpt-5.5            1M       128K     yes       yes
"""
# PI_TABLE plus a model from the shipped value type and one for the test types.
TYPES_TABLE = PI_TABLE + """\
anthropic     claude-sonnet-5-5  1M       128K     yes       yes
xai           grok-4.7           500K     500K     yes       yes
"""

FAKE_TOOL = r'''
import json
import os
import sys

name = os.path.basename(sys.argv[0])
key = name + " " + " ".join(sys.argv[1:3])
with open(os.environ["SPARKS_TEST_SPAWN_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps([name, *sys.argv[1:]]) + "\n")
with open(os.environ["SPARKS_TEST_SPAWN_LOG"], encoding="utf-8") as log:
    seen = sum(1 for line in log if (lambda c: " ".join([c[0], *c[1:3]]))(json.loads(line)) == key)
with open(os.environ["SPARKS_TEST_SPAWN_REPLIES"], encoding="utf-8") as config:
    replies = json.load(config)
reply = replies.get(key)
if key == "herdr agent get" and reply == "run-protocol":
    with open(os.environ["SPARKS_TEST_SPAWN_LOG"], encoding="utf-8") as log:
        calls = [json.loads(line) for line in log]
    last_start = max(i for i, c in enumerate(calls) if c[1:3] == ["agent", "start"])
    prompted = any(c[1:3] == ["agent", "prompt"] for c in calls[last_start:])
    reply = {"stdout": json.dumps({"result": {"agent": {"agent_status": "idle",
        "tokens": {"sparks_run": "1:ok" if prompted else "0:ready"}}}})}
if isinstance(reply, list):  # one reply per call, the last one repeating
    reply = reply[min(seen, len(reply)) - 1]
if reply is None:
    sys.stderr.write("fake: unexpected argv\n")
    sys.exit(73)
sys.stdout.write(reply.get("stdout", ""))
sys.stderr.write(reply.get("stderr", ""))
sys.exit(reply.get("code", 0))
'''

AGENT_NAME = re.compile(r"[a-z][a-z0-9_-]{0,31}")
EXTENSION = str(ROOT / "pi" / "extensions" / "sparks-api-error-blocked.ts")
CREATED = {"result": {"tab": {"tab_id": "w1:t9"}, "root_pane": {"pane_id": "w1:p9"}}}
START_FAILED = {"code": 1, "stderr": '{"error":{"message":"timed out"}}\n'}
CLOSED = {"stdout": '{"result":{"type":"ok"}}'}


def agent_info(status, tokens=None):
    agent = {"agent": "pi", "agent_status": status, "pane_id": "w1:p9"}
    if tokens is not None:
        agent["tokens"] = tokens
    return {"stdout": json.dumps({"result": {"type": "agent_info", "agent": agent}})}


def sparks_prompt(name="reviewer"):
    return cli.SPARKS_PROMPT.format(name=name)


def tail(name="reviewer", *prompts):
    """The pi arguments every persona ends with: the extension and the system prompts."""
    args = ["-e", EXTENSION, "--append-system-prompt", sparks_prompt(name)]
    for prompt in prompts:
        args += ["--append-system-prompt", prompt]
    return args


class FakeSpawn:
    """A project with .sparks/agents.toml, run from a subdirectory, and fake pi and herdr."""

    def __init__(self, directory, monkeypatch):
        self.bin_dir = directory / "fake-bin"
        self.bin_dir.mkdir()
        for tool in ("pi", "herdr"):
            path = self.bin_dir / tool
            path.write_text(f"#!{sys.executable}\n" + FAKE_TOOL, encoding="utf-8")
            path.chmod(0o755)
        self.log = directory / "spawn-argv.jsonl"
        self.replies_path = directory / "spawn-replies.json"
        self.home = directory / "home"
        self.home.mkdir()
        self.project = directory / "project"
        self.cwd = self.project / "deep" / "er"
        self.cwd.mkdir(parents=True)
        (self.project / ".git").mkdir()  # the lookup stops here
        (self.project / ".sparks").mkdir()
        (self.project / ".sparks").chmod(0o755)
        self.config = self.project / ".sparks" / "agents.toml"
        self.types = self.project / ".sparks" / "model-types.toml"
        monkeypatch.setenv("PATH", str(self.bin_dir) + os.pathsep + os.environ.get("PATH", ""))
        monkeypatch.setenv("SPARKS_TEST_SPAWN_LOG", str(self.log))
        monkeypatch.setenv("SPARKS_TEST_SPAWN_REPLIES", str(self.replies_path))
        monkeypatch.setenv("HOME", str(self.home))  # no user skills leak in
        monkeypatch.delenv("PI_CODING_AGENT_DIR", raising=False)
        monkeypatch.delenv("HERDR_WORKSPACE_ID", raising=False)
        self.replies(start_code=0)
        self.personas(persona())

    def personas(self, text, path=None):
        path = path or self.config
        path.parent.mkdir(exist_ok=True)
        path.parent.chmod(0o755)
        path.write_text(text, encoding="utf-8")
        path.chmod(0o644)

    def model_types(self, text):
        self.personas(text, path=self.types)

    def replies(self, start_code=0, table=PI_TABLE, overrides=None):
        """overrides: replies keyed by "<tool> <argv 1> <argv 2>", such as "herdr tab create".
        A list holds one reply per call."""
        replies = {"pi --list-models": {"stdout": table}}
        replies["herdr tab create"] = {"stdout": json.dumps(CREATED)}
        replies["herdr agent start"] = {"stdout": "{}"} if start_code == 0 else START_FAILED
        replies["herdr pane read"] = {"stdout": "pane says why\n"}
        replies["herdr tab close"] = CLOSED
        replies["herdr agent prompt"] = {"stdout": "{}"}
        replies["herdr agent get"] = "run-protocol"
        replies.update(overrides or {})
        self.replies_path.write_text(json.dumps(replies), encoding="utf-8")

    def run(self, *args, **kwargs):
        return sparks("agent", "spawn", *args, cwd=self.cwd, timeout=60, **kwargs)

    def plan(self, *args):
        result = self.run(*args, "--dry-run")
        assert (result.returncode, result.stderr) == (0, ""), result.stderr
        assert result.stdout.count("\n") == 1
        return json.loads(result.stdout)

    @property
    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def herdr_calls(self):
        return [call for call in self.calls if call[0] == "herdr"]


@pytest.fixture
def fake_spawn(tmp_path, monkeypatch):
    if os.name != "posix":
        pytest.skip("fake executables use a POSIX shebang")
    return FakeSpawn(tmp_path, monkeypatch)


def persona(table="reviewer", **keys):
    body = {"role": "Reviews", "model_type": "fast", "model": "claude-opus-5", "effort": "high", **keys}
    lines = [f"{key} = {json.dumps(value)}" for key, value in body.items() if value is not None]
    return f"[{table}]\n" + "\n".join(lines) + "\n"


def test_spawn_dry_run_finds_the_parent_config_and_builds_the_pi_command(fake_spawn):
    fake_spawn.personas(persona(provider="anthropic", system_prompt="Review only. Don't edit."))
    plan = fake_spawn.plan("reviewer")
    assert set(plan) == {
        "agent", "config", "model_types", "cwd", "model_type", "chain", "chosen", "command", "timeout_ms",
    }
    assert plan["command"] == [
        "pi", "--provider", "anthropic", "--model", "claude-opus-5", "--thinking", "high",
        *tail("reviewer", "Review only. Don't edit."),
    ]
    assert Path(plan["config"]) == fake_spawn.config
    assert plan["model_types"] == [str(ROOT / "defaults" / "model-types.toml")]
    assert Path(plan["cwd"]).resolve() == fake_spawn.cwd.resolve()
    assert (plan["model_type"], plan["chosen"], plan["timeout_ms"]) == ("fast", 0, 30000)
    assert plan["chain"][0]["type"] == "persona" and plan["chain"][0]["command"] == plan["command"]
    assert re.fullmatch(r"reviewer-[0-9a-f]{4}", plan["agent"]) and AGENT_NAME.fullmatch(plan["agent"])
    assert fake_spawn.calls == [["pi", "--list-models"]]


def test_spawn_injected_prompt_tells_the_agent_to_read_and_verify_against_sparks():
    prompt = sparks_prompt("implementer")
    assert "implementer persona" in prompt
    assert "read the sparks.json in that directory and in each parent directory" in prompt
    assert "load the repository-root sparks.json and the sparks.json of every directory that holds a changed file" in prompt
    assert "Write a task-scoped verification skill file just in time" in prompt
    assert ".sparks/verify/<task>.md" in prompt
    assert "Then run that procedure" in prompt
    assert "explicit handoff" in prompt
    assert not cli.CONTROL.search(prompt)


@pytest.mark.parametrize(("effort", "thinking"), [
    ("none", "off"), ("minimal", "minimal"), ("low", "low"), ("medium", "medium"), ("high", "high"),
    ("xhigh", "xhigh"), ("extra high", "xhigh"), ("Extra-High", "xhigh"), ("extrahigh", "xhigh"), ("max", "max"),
])
def test_spawn_effort_maps_to_a_pi_thinking_level(fake_spawn, effort, thinking):
    fake_spawn.personas(persona(effort=effort))
    command = fake_spawn.plan("reviewer")["command"]
    assert command[command.index("--thinking") + 1] == thinking


def test_spawn_provider_comes_from_pi_when_one_serves_the_model_and_is_required_when_several_do(fake_spawn):
    fake_spawn.personas(persona(model="gpt-5.5"))
    result = fake_spawn.run("reviewer", "--dry-run")
    assert_rejected(result, "more than one pi provider serves gpt-5.5; set provider to one of: openai, openai-codex")
    fake_spawn.personas(persona(model="gpt-5.5", provider="openai-codex"))
    assert fake_spawn.plan("reviewer")["command"][1:5] == ["--provider", "openai-codex", "--model", "gpt-5.5"]
    fake_spawn.personas(persona())
    assert fake_spawn.plan("reviewer")["command"][1:3] == ["--provider", "anthropic"]


@pytest.mark.parametrize(("keys", "message"), [
    ({"effort": "ultra"}, "pi has no ultra thinking level"),
    ({"effort": "fastest"}, "unknown effort"),
    ({"model_type": None}, "model_type must be specified"),
    ({"model_type": "slow"}, "unknown model_type slow; types: powerful, value, fast"),
    ({"effort": None}, "effort must be specified with model"),
    ({"model": None}, "effort is set without model"),
    ({"model": None, "effort": None, "provider": "anthropic"}, "provider is set without model"),
    ({"role": None}, "role must be specified"),
    ({"model": "claude-opus-5:high"}, "model must not include effort"),
    ({"model": "claude-opus-5-fast"}, "model must not include speed"),
    ({"speed": "fast"}, "personas have no speed"),
    ({"temperature": "1"}, "unknown key"),
    ({"agent": "claude"}, "only pi is supported"),
    ({"provider": ""}, "provider is empty"),
    ({"effort": 3}, "effort must be a string"),
    ({"skills": "spark-verification"}, "skills must be a list of strings"),
    ({"provider": "xai"}, "pi lists no xai/claude-opus-5; providers that serve it: anthropic"),
    ({"model": "claude-opus-9"}, "no combo for model type fast is available: persona claude-opus-9: pi lists no"),
    ({"model": "gpt-4o", "provider": "openai"}, "without thinking; set effort to none"),
    ({"system_prompt": "two\nlines"}, "system_prompt must be one line"),
    ({"system_prompt": "notes.md"}, "system_prompt names an existing path"),
])
def test_spawn_refuses_a_persona_pi_cannot_run_and_launches_nothing(fake_spawn, keys, message):
    (fake_spawn.cwd / "notes.md").write_text("not a prompt\n", encoding="utf-8")
    fake_spawn.personas(persona(**keys))
    result = fake_spawn.run("reviewer")
    assert_rejected(result, message)
    assert fake_spawn.herdr_calls() == []


def test_spawn_model_without_thinking_runs_at_effort_none(fake_spawn):
    fake_spawn.personas(persona(model="gpt-4o", provider="openai", effort="none"))
    command = fake_spawn.plan("reviewer")["command"]
    assert command[1:7] == ["--provider", "openai", "--model", "gpt-4o", "--thinking", "off"]


def test_spawn_unknown_type_lists_the_project_and_default_personas(fake_spawn):
    fake_spawn.personas(persona() + persona("implementer"))
    result = fake_spawn.run("writer")
    assert_rejected(result, "no persona writer; personas: reviewer, implementer; "
                            "plugin defaults: spec-writer, implementer, reviewer")
    assert fake_spawn.calls == []


@pytest.mark.parametrize(("text", "name", "message"), [
    (None, "writer", "no persona writer: no .sparks/agents.toml in"),
    ("[reviewer\n", "reviewer", "invalid TOML"),
    (persona("Reviewer"), "Reviewer", "a persona name is a lowercase letter"),
])
def test_spawn_refuses_a_missing_or_broken_config(fake_spawn, text, name, message):
    if text is None:
        fake_spawn.config.unlink()
    else:
        fake_spawn.personas(text)
    result = fake_spawn.run(name)
    assert_rejected(result, message)
    assert fake_spawn.calls == []


def test_spawn_additional_flags_are_split_on_whitespace_and_appended(fake_spawn):
    plan = fake_spawn.plan("--additional-flags", "--offline   --name 'two words'", "reviewer")
    assert plan["command"][-4:] == ["--offline", "--name", "'two", "words'"]
    assert fake_spawn.plan("reviewer", "--additional-flags", "--no-session")["command"][-1] == "--no-session"


@pytest.mark.parametrize(("flags", "key"), [
    ("--model gpt-5.5", "model"), ("--offline --model=gpt-5.5", "model"), ("--effort high", "effort"),
    ("--speed fast", "model"), ("--provider openai", "provider"), ("--thinking=max", "effort"),
    ("--system-prompt x", "system_prompt"), ("--append-system-prompt x", "system_prompt"),
    ("--models opus:max", "model"), ("--offline --models=anthropic/*", "model"),
    ("--tools read", "allowed_tools"), ("-t read", "allowed_tools"), ("--tools=read,bash", "allowed_tools"),
    ("--no-tools", "allowed_tools"), ("-nt", "allowed_tools"), ("--no-builtin-tools", "allowed_tools"),
    ("-nbt", "allowed_tools"), ("--exclude-tools write", "forbidden_tools"), ("-xt write", "forbidden_tools"),
    ("--no-mcp", "allowed_mcp"), ("--skill ./x", "skills"), ("--no-skills", "skills"), ("-ns", "skills"),
])
def test_spawn_refuses_persona_flags_smuggled_into_additional_flags(fake_spawn, flags, key):
    result = fake_spawn.run("reviewer", "--additional-flags", flags)
    assert_rejected(result, f"is set by the persona in .sparks/agents.toml ({key})")
    assert fake_spawn.calls == []


@pytest.mark.parametrize(("flags", "reason"), [
    ("-p hello", "print mode"), ("--print", "print mode"), ("--offline --print=hi", "print mode"),
    ("--mode rpc", "without its interactive interface"), ("--mode=json", "without its interactive interface"),
    ("--export out.html", "export a session and exit"), ("--list-models", "list models and exit"),
    ("-h", "print its help and exit"), ("--help", "print its help and exit"),
    ("-v", "print its version and exit"), ("--version", "print its version and exit"),
    ("--api-key sk-secret", "would show the key"), ("--api-key=sk-secret", "would show the key"),
    ("-e ./x.ts", "loads or disables pi extensions"), ("--extension=./x.ts", "loads or disables pi extensions"),
    ("--no-extensions", "loads or disables pi extensions"), ("-ne", "loads or disables pi extensions"),
])
def test_spawn_refuses_additional_flags_that_end_the_interactive_launch_or_leak_a_key(fake_spawn, flags, reason):
    result = fake_spawn.run("reviewer", "--additional-flags", flags)
    flag = next(word for word in flags.split() if word.split("=")[0] in cli.REFUSED_FLAGS).split("=")[0]
    assert_rejected(result, f"--additional-flags: {flag} is refused: it ")
    assert reason in result.stderr
    assert "sk-secret" not in result.stderr
    assert fake_spawn.calls == []


def test_spawn_passes_other_pi_flags_through(fake_spawn):
    flags = "--offline --no-context-files --name probe --no-session"
    assert fake_spawn.plan("reviewer", "--additional-flags", flags)["command"][-5:] == flags.split()


@pytest.mark.parametrize("args", [
    ["--timeout", "3"], ["--timeout", "3.0004"], ["--timeout", "3.0005"], ["--timeout", "300.0006"],
    ["--timeout", "300.5"], ["--timeout", "nan"], ["--timeout", "inf"], ["--timeout", "soon"],
    ["--additional-flags", "a", "--additional-flags", "b"], ["--prompt", "a", "--prompt", "b"],
    ["--watch", "10"], ["--prompt", "go", "--watch", "3"], ["--prompt", "go", "--watch", "301"], [],
])
def test_spawn_usage_errors_exit_2_and_call_nothing(fake_spawn, args):
    result = fake_spawn.run(*args, *(["reviewer"] if args else []))
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("usage: sparks agent spawn")
    assert fake_spawn.calls == []


@pytest.mark.parametrize("args", [
    ["--additional-flag", "--offline"], ["--add=--offline"], ["--additional-flag=--offline"], ["--time", "9"],
    ["--prom", "go"],
])
def test_spawn_refuses_abbreviated_options(fake_spawn, args):
    """allow_abbrev=False: only full spellings are bound as one argument."""
    result = fake_spawn.run(*args, "reviewer")
    assert result.returncode == 2
    assert result.stdout == ""
    assert "error: unrecognized arguments: " + args[0] in result.stderr
    assert fake_spawn.calls == []


@pytest.mark.parametrize(("seconds", "ms"), [
    ("3.5", 3500), ("3.0006", 3001), ("300", 300000), ("300.0004", 300000), ("90", 90000),
])
def test_spawn_timeout_bounds_are_open_at_3_and_closed_at_300(fake_spawn, seconds, ms):
    assert fake_spawn.plan("reviewer", "--timeout", seconds)["timeout_ms"] == ms


def test_spawn_opens_a_tab_in_the_caller_directory_and_starts_pi_in_its_pane(fake_spawn, monkeypatch):
    monkeypatch.setenv("HERDR_WORKSPACE_ID", "w1")
    result = fake_spawn.run("reviewer", "--timeout", "45", "--additional-flags", "--offline")
    assert (result.returncode, result.stderr) == (0, ""), result.stderr
    out = json.loads(result.stdout)
    assert set(out) == {"agent", "tab", "pane", "command", "model_type", "combo", "attempts"}
    assert (out["tab"], out["pane"], out["model_type"]) == ("w1:t9", "w1:p9", "fast")
    pi_args = ["--provider", "anthropic", "--model", "claude-opus-5", "--thinking", "high", *tail(), "--offline"]
    assert out["command"] == ["pi", *pi_args]
    combo = {"type": "persona", "provider": "anthropic", "model": "claude-opus-5", "effort": "high"}
    assert out["combo"] == combo
    assert out["attempts"] == [{**combo, "result": "started"}]
    create, start = fake_spawn.herdr_calls()
    assert create[:5] == ["herdr", "tab", "create", "--workspace", "w1"]
    assert create[5] == "--cwd" and Path(create[6]).resolve() == fake_spawn.cwd.resolve()
    assert create[7:] == ["--no-focus"]
    assert start == [
        "herdr", "agent", "start", out["agent"], "--kind", "pi", "--pane", "w1:p9",
        "--timeout", "45000", "--", *pi_args,
    ]


def test_spawn_failed_start_closes_the_tab_and_reports_every_attempt(fake_spawn):
    fake_spawn.replies(start_code=1)
    result = fake_spawn.run("reviewer")
    assert result.returncode == 1
    assert "timed out" in result.stderr and "pane says why" in result.stderr
    assert "sparks: persona anthropic/claude-opus-5 high: start failed (exit 1); tab w1:t9 closed" in result.stderr
    assert result.stderr.endswith("sparks: every combo for model type fast failed\n")
    out = json.loads(result.stdout)
    assert out["agent"] is None and out["left_open"] == []
    results = [attempt["result"] for attempt in out["attempts"]]
    assert results[0] == "start failed (exit 1)"
    assert all(item.startswith("unavailable: pi lists no ") for item in results[1:]) and len(results) == 8
    assert [call[1:3] for call in fake_spawn.herdr_calls()] == [
        ["tab", "create"], ["agent", "start"], ["pane", "read"], ["tab", "close"],
    ]


def test_spawn_a_tab_herdr_cannot_close_is_reported_left_open(fake_spawn):
    fake_spawn.replies(start_code=1, overrides={"herdr tab close": {"code": 1, "stderr": "nope\n"}})
    result = fake_spawn.run("reviewer")
    assert result.returncode == 1
    assert "herdr tab close failed: nope; tab w1:t9 is left open" in result.stderr
    assert result.stderr.endswith("cleanup failed; stopping fallback\n")
    assert json.loads(result.stdout)["left_open"] == ["w1:t9"]


def test_spawn_start_that_times_out_in_sparks_closes_the_tab(monkeypatch, capsys):
    """The SpawnError branch: herdr agent start overran sparks' own subprocess timeout."""
    def fake_run(argv, timeout, what):
        if argv[1:3] == ["tab", "create"]:
            return subprocess.CompletedProcess(argv, 0, json.dumps(CREATED), "")
        if argv[1:3] == ["agent", "start"]:
            assert timeout == 4 + cli.CALL_TIMEOUT
            raise cli.SpawnError(f"{what}: timed out after {timeout:g} seconds")
        if argv[1:3] == ["tab", "close"]:
            return subprocess.CompletedProcess(argv, 0, CLOSED["stdout"], "")
        return subprocess.CompletedProcess(argv, 0, "pane says why\n", "")

    monkeypatch.setattr(cli, "_run", fake_run)
    monkeypatch.delenv("HERDR_WORKSPACE_ID", raising=False)
    step = {"type": "t", "provider": "p", "model": "m", "effort": "low", "available": True,
            "command": ["pi", "--offline"]}
    plan = {"agent": "reviewer-0a1b", "cwd": "/x", "timeout_ms": 4000, "model_type": "t",
            "chosen": 0, "chain": [step]}
    code, out = cli.spawn(plan)
    assert code == 1
    assert out["attempts"][0]["result"] == "start failed (herdr agent start: timed out after 34 seconds)"
    assert (out["attempts"][0]["tab"], out["attempts"][0]["closed"]) == ("w1:t9", True)
    err = capsys.readouterr().err
    assert "pane says why" in err and "tab w1:t9 closed" in err


@pytest.mark.parametrize(("created", "left"), [
    ({"tab": {"tab_id": "w1:t9"}}, "; tab w1:t9 is left open"),
    ({"tab": {"tab_id": "w1:t9"}, "root_pane": {}}, "; tab w1:t9 is left open"),
    ({"root_pane": {"pane_id": "w1:p9"}}, ""),
])
def test_spawn_unusable_tab_create_reply_names_the_tab_left_open(fake_spawn, created, left):
    fake_spawn.replies(overrides={"herdr tab create": {"stdout": json.dumps({"result": created})}})
    result = fake_spawn.run("reviewer")
    assert_rejected(result, f"herdr tab create did not return a tab and its root pane{left}\n")
    assert [call[1:3] for call in fake_spawn.herdr_calls()] == [["tab", "create"]]


@pytest.mark.parametrize("reply", [
    {"code": 1, "stderr": '{"error":{"message":"no such workspace"}}\n'},
    {"code": 0, "stdout": '{"error":{"message":"no such workspace"}}\n'},
])
def test_spawn_failed_tab_create_starts_nothing(fake_spawn, reply):
    fake_spawn.replies(overrides={"herdr tab create": reply})
    result = fake_spawn.run("reviewer")
    assert_rejected(result, "herdr tab create failed: no such workspace")
    assert [call[1:3] for call in fake_spawn.herdr_calls()] == [["tab", "create"]]


@pytest.mark.parametrize(("reply", "message"), [
    ({"code": 2, "stderr": "pi: config broken\n"}, "pi --list-models failed: pi: config broken"),
    ({"code": 1}, "pi --list-models failed: exit 1"),
    ({"stdout": "No models available\n"}, "no combo for model type fast is available"),
])
def test_spawn_pi_list_models_failure_is_refused_and_launches_nothing(fake_spawn, reply, message):
    fake_spawn.replies(overrides={"pi --list-models": reply})
    assert_rejected(fake_spawn.run("reviewer"), message)
    assert fake_spawn.herdr_calls() == []


def test_spawn_finds_the_config_in_the_cwd_itself(fake_spawn):
    nearer = fake_spawn.cwd / ".sparks" / "agents.toml"
    fake_spawn.personas(persona(effort="low"), path=nearer)
    plan = fake_spawn.plan("reviewer")
    assert Path(plan["config"]) == nearer
    assert plan["command"][5:7] == ["--thinking", "low"]


@pytest.mark.parametrize("git", ["directory", "file"])
def test_spawn_lookup_stops_at_the_git_top_level(fake_spawn, git):
    outer = fake_spawn.project.parent / ".sparks" / "agents.toml"
    fake_spawn.personas(persona("probe"), path=outer)
    fake_spawn.config.unlink()
    if git == "file":  # a worktree or submodule has a .git file
        (fake_spawn.project / ".git").rmdir()
        (fake_spawn.project / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
    result = fake_spawn.run("probe", "--dry-run")
    assert_rejected(result, f"or a parent up to the git top level {fake_spawn.project},")
    assert fake_spawn.calls == []
    # Outside a repository the walk goes on, and finds the outer file.
    git_path = fake_spawn.project / ".git"
    git_path.rmdir() if git_path.is_dir() else git_path.unlink()
    assert Path(fake_spawn.plan("probe")["config"]) == outer


@pytest.mark.parametrize("target", ["file", "directory"])
@pytest.mark.parametrize("mode", [0o020, 0o002])
def test_spawn_refuses_a_config_group_or_others_can_write(fake_spawn, target, mode):
    item = fake_spawn.config if target == "file" else fake_spawn.config.parent
    item.chmod(item.stat().st_mode | mode)
    result = fake_spawn.run("reviewer", "--dry-run")
    assert_rejected(result, f"{item}: writable by group or others; refusing it (chmod go-w {item})")
    assert fake_spawn.calls == []


def test_spawn_refuses_a_model_types_file_group_or_others_can_write(fake_spawn):
    fake_spawn.model_types('[fast]\n[[fast.combos]]\nprovider = "xai"\nmodel = "grok-4.7"\neffort = "low"\n')
    fake_spawn.types.chmod(0o666)
    result = fake_spawn.run("reviewer", "--dry-run")
    assert_rejected(result, f"{fake_spawn.types}: writable by group or others")
    assert fake_spawn.calls == []


@pytest.mark.skipif(not hasattr(os, "getuid"), reason="needs POSIX uids")
@pytest.mark.parametrize("target", ["file", "directory"])
def test_spawn_refuses_a_config_another_user_owns(tmp_path, monkeypatch, target):
    config = tmp_path / ".sparks" / "agents.toml"
    config.parent.mkdir(mode=0o755)
    config.write_text(persona(), encoding="utf-8")
    config.chmod(0o644)
    other = os.getuid() + 1
    owner = config if target == "file" else config.parent
    real_stat = Path.stat

    def fake_stat(self, *args, **kwargs):
        info = real_stat(self, *args, **kwargs)
        if self == owner:
            return os.stat_result((info.st_mode, info.st_ino, info.st_dev, info.st_nlink, other, *info[5:]))
        return info

    monkeypatch.setattr(Path, "stat", fake_stat)
    with pytest.raises(cli.SpawnError, match=re.escape(f"{owner}: owned by uid {other}, not you")):
        cli._nearest(tmp_path, cli.AGENTS_FILE)


def test_spawn_name_key_must_equal_the_table_name(fake_spawn):
    fake_spawn.personas(persona(name="reviewer"))
    assert fake_spawn.plan("reviewer")["command"][0] == "pi"
    fake_spawn.personas(persona(name="critic"))
    fake_spawn.log.unlink()
    result = fake_spawn.run("reviewer")
    assert_rejected(result, "[reviewer]: name is critic; it must equal the table name reviewer")
    assert fake_spawn.calls == []


def test_spawn_golden_example_has_no_personas_and_its_commented_examples_run(fake_spawn):
    golden = (ROOT / "defaults" / "agent.toml").read_text(encoding="utf-8")
    fake_spawn.personas(golden)
    fake_spawn.replies(table=TYPES_TABLE)
    assert_rejected(fake_spawn.run("critic"), "no persona critic; personas: none")
    examples = golden.split("# Examples (uncomment to use):\n", 1)[1]
    fake_spawn.personas("".join(re.sub(r"^# ?", "", line) for line in examples.splitlines(True)))
    personas = tomllib.loads(fake_spawn.config.read_text(encoding="utf-8"))
    assert personas, "the golden example lost its commented examples"
    for name in personas:
        assert fake_spawn.plan(name)["command"][0] == "pi"


# persona fields: tools, MCP, skills, directories

RESOURCE_TOOLS = "list_mcp_resources,list_mcp_resource_templates,read_mcp_resource"


def test_spawn_maps_tools_mcp_skills_and_directories_to_pi_flags(fake_spawn):
    fake_spawn.personas(persona(
        allowed_tools=["read", "bash", "grep"], forbidden_tools=["write"],
        allowed_mcp=["radius", "dev-docs"], forbidden_mcp=["mcp__radius__delete*"],
        skills=["spark-verification", "sparks-postcall"], allowed_directories=["src", "docs/api"],
        system_prompt="Be brief.",
    ))
    command = fake_spawn.plan("reviewer")["command"]
    assert command[7:] == [
        "--tools", "read,bash,grep,mcp__radius__*,mcp__dev_docs__*",
        "--exclude-tools", "write,list_mcp_resources,list_mcp_resource_templates,read_mcp_resource,mcp__radius__delete*",
        "--no-skills",
        "--skill", str(ROOT / "skills" / "spark-verification"),
        "--skill", str(ROOT / "skills" / "sparks-postcall"),
        "-e", EXTENSION,
        "--append-system-prompt", sparks_prompt(),
        "--append-system-prompt", cli.DIRECTORIES_PROMPT.format(directories="src, docs/api"),
        "--append-system-prompt", "Be brief.",
    ]


@pytest.mark.parametrize(("keys", "flags"), [
    ({}, []),
    ({"allowed_tools": []}, ["--no-tools"]),
    ({"allowed_tools": [], "allowed_mcp": ["radius"]}, ["--tools", "mcp__radius__*", "--exclude-tools", RESOURCE_TOOLS]),
    ({"allowed_mcp": []}, ["--exclude-tools", RESOURCE_TOOLS, "--no-mcp"]),
    ({"allowed_tools": ["read", "edit"], "allowed_mcp": []}, ["--tools", "read,edit", "--exclude-tools", RESOURCE_TOOLS, "--no-mcp"]),
    ({"forbidden_mcp": ["radius"]}, ["--exclude-tools", RESOURCE_TOOLS + ",mcp__radius__*"]),
    ({"skills": []}, ["--no-skills"]),
])
def test_spawn_list_fields_map_to_the_documented_pi_flag(fake_spawn, keys, flags):
    fake_spawn.personas(persona(**keys))
    command = fake_spawn.plan("reviewer")["command"]
    assert command[7:command.index("-e")] == flags


@pytest.mark.parametrize(("keys", "message"), [
    ({"allowed_tools": ["+read"]}, "allowed_tools entry +read is not a tool name or * pattern"),
    ({"allowed_tools": ["read,bash"]}, "is not a tool name or * pattern"),
    ({"forbidden_tools": ["mcp__radius__x"]}, "is an MCP tool; put MCP servers in forbidden_mcp"),
    ({"allowed_tools": ["read"], "forbidden_tools": ["read"]}, "tool read is both allowed and forbidden"),
    ({"allowed_tools": ["read"], "allowed_mcp": ["a"], "forbidden_mcp": ["a"]}, "is both allowed and forbidden"),
    ({"allowed_mcp": ["radius"]}, "allowed_mcp needs allowed_tools"),
    ({"allowed_tools": ["read"], "allowed_mcp": ["bad server"]}, "is not an MCP server name"),
    ({"allowed_tools": ["read", "read"]}, "allowed_tools lists read twice"),
    ({"allowed_tools": [""]}, "allowed_tools has an empty entry"),
    ({"allowed_tools": [1]}, "allowed_tools must be a list of strings"),
    ({"skills": ["no-such-skill"]}, "no skill no-such-skill in .pi/skills or .agents/skills"),
    ({"skills": ["../escape"]}, "skills entry ../escape is not a skill name"),
    ({"skills": ["spark-verification"], "allowed_tools": ["grep"]}, "skills need the read or bash tool"),
    ({"skills": ["spark-verification"], "forbidden_tools": ["read", "bash"]}, "skills need the read or bash tool"),
    ({"allowed_directories": []}, "allowed_directories is empty"),
    ({"allowed_directories": ["src\tx"]}, "has a control character"),
])
def test_spawn_refuses_bad_tool_mcp_skill_and_directory_fields(fake_spawn, keys, message):
    fake_spawn.personas(persona(**keys))
    assert_rejected(fake_spawn.run("reviewer", "--dry-run"), message)
    assert fake_spawn.herdr_calls() == []


def test_spawn_skill_lookup_prefers_the_project_then_the_plugin_then_the_user(fake_spawn, monkeypatch):
    def make(root, name):
        (root / name).mkdir(parents=True)
        (root / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n", encoding="utf-8")
        return root / name

    project = make(fake_spawn.project / ".agents" / "skills", "spark-verification")
    nearer = make(fake_spawn.cwd / ".pi" / "skills", "only-here")
    agent_dir = fake_spawn.home / "agent-dir"
    user = make(agent_dir / "skills", "mine")
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(agent_dir))
    agents = make(fake_spawn.home / ".agents" / "skills", "shared")
    fake_spawn.personas(persona(skills=["spark-verification", "only-here", "sparks-postcall", "mine", "shared"]))
    command = fake_spawn.plan("reviewer")["command"]
    skills = [command[i + 1] for i, word in enumerate(command) if word == "--skill"]
    assert skills == [str(project), str(nearer), str(ROOT / "skills" / "sparks-postcall"), str(user), str(agents)]


# model types


TYPES = """\
[cheap]
description = "a user's own type"
fallback = ["sharp"]

[[cheap.combos]]
provider = "xai"
model = "grok-9"
effort = "low"
service_tier = "flex"

[[cheap.combos]]
provider = "xai"
model = "grok-4.7"
effort = "low"
service_tier = "flex"

[sharp]
fallback = ["cheap"]

[[sharp.combos]]
provider = "anthropic"
model = "claude-sonnet-5-5"
effort = "high"

[[sharp.combos]]
provider = "xai"
model = "grok-4.7"
effort = "low"
"""


def test_spawn_custom_model_type_resolves_its_chain_and_skips_an_unavailable_model(fake_spawn):
    fake_spawn.model_types(TYPES)
    fake_spawn.replies(table=TYPES_TABLE)
    fake_spawn.personas(persona(model_type="cheap", model=None, effort=None))
    plan = fake_spawn.plan("reviewer")
    assert plan["model_types"] == [str(ROOT / "defaults" / "model-types.toml"), str(fake_spawn.types)]
    shown = [(s["type"], s["provider"], s["model"], s["effort"], s["available"]) for s in plan["chain"]]
    assert shown == [  # cheap's combos, then sharp's; the repeated grok-4.7 low is dropped
        ("cheap", "xai", "grok-9", "low", False),
        ("cheap", "xai", "grok-4.7", "low", True),
        ("sharp", "anthropic", "claude-sonnet-5-5", "high", True),
    ]
    assert plan["chain"][0]["reason"] == "pi lists no xai/grok-9"
    assert plan["chosen"] == 1
    assert plan["chain"][1]["service_tier"] == "flex"
    assert plan["command"][1:7] == ["--provider", "xai", "--model", "grok-4.7", "--thinking", "low"]
    assert "flex" not in plan["command"]  # pi has no service tier flag


@pytest.mark.parametrize(("provider", "model", "own_effort", "bucket_effort"), [
    (None, "claude-sonnet-5-5", "high", "high"),
    ("ANTHROPIC", "CLAUDE-SONNET-5-5", "HIGH", "high"),
    (None, "claude-sonnet-5-5", "Extra  High", "xhigh"),
    ("Anthropic", "claude-sonnet-5-5", "extra-high", "extrahigh"),
])
def test_spawn_deduplicates_resolved_invocations(fake_spawn, provider, model, own_effort, bucket_effort):
    fake_spawn.model_types(TYPES.replace('effort = "high"', f'effort = "{bucket_effort}"'))
    fake_spawn.personas(persona(model_type="sharp", provider=provider, model=model, effort=own_effort))
    fake_spawn.replies(table=TYPES_TABLE, overrides={"herdr agent start": [START_FAILED, {"stdout": "{}"}]})
    plan = fake_spawn.plan("reviewer")
    assert [(s["type"], s["model"], s["available"]) for s in plan["chain"]] == [
        ("persona", "claude-sonnet-5-5", True), ("sharp", "grok-4.7", True),
        ("cheap", "grok-9", False),
    ]
    assert plan["chosen"] == 0
    assert plan["chain"][0]["effort"] == own_effort  # first occurrence wins
    result = fake_spawn.run("reviewer")
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert [a["model"] for a in out["attempts"]] == ["claude-sonnet-5-5", "grok-4.7"]
    starts = [c for c in fake_spawn.herdr_calls() if c[1:3] == ["agent", "start"]]
    assert len(starts) == 2
    assert sum(c[1:3] == ["tab", "close"] for c in fake_spawn.herdr_calls()) == 1


def test_spawn_project_type_replaces_the_shipped_type_of_that_name(fake_spawn):
    fake_spawn.model_types('[fast]\n[[fast.combos]]\nprovider = "xai"\nmodel = "grok-4.7"\neffort = "minimal"\n')
    fake_spawn.personas(persona(model="claude-opus-9"))
    fake_spawn.replies(table=TYPES_TABLE)
    plan = fake_spawn.plan("reviewer")
    assert [(s["type"], s["model"]) for s in plan["chain"]] == [("persona", "claude-opus-9"), ("fast", "grok-4.7")]
    assert plan["command"][1:7] == ["--provider", "xai", "--model", "grok-4.7", "--thinking", "minimal"]


def test_spawn_default_model_types_fall_back_in_escalation_order(fake_spawn):
    fake_spawn.personas(persona(model_type="fast", model=None, effort=None))
    fake_spawn.replies(table=TYPES_TABLE)
    plan = fake_spawn.plan("reviewer")
    types = list(dict.fromkeys(step["type"] for step in plan["chain"]))
    assert types == ["fast", "value", "powerful"]
    chosen = plan["chain"][plan["chosen"]]
    assert (chosen["type"], chosen["model"]) == ("value", "claude-sonnet-5-5")  # the first one fake pi lists


@pytest.mark.parametrize(("text", "message"), [
    ("[fast]\n", "combos must be one or more [[fast.combos]] tables"),
    ('[fast]\nfallback = ["nope"]\n[[fast.combos]]\nprovider = "x"\nmodel = "m"\neffort = "low"\n',
     "fallback names unknown model type nope"),
    ('[fast]\nfallback = ["fast"]\n[[fast.combos]]\nprovider = "x"\nmodel = "m"\neffort = "low"\n',
     "fallback names the type itself"),
    ('[fast]\n[[fast.combos]]\nprovider = "x"\nmodel = "m"\n', "combo 1: effort must be specified"),
    ('[fast]\n[[fast.combos]]\nprovider = "x"\nmodel = "m"\neffort = "ultra"\n', "pi has no ultra thinking level"),
    ('[fast]\n[[fast.combos]]\nprovider = "x"\nmodel = "m:high"\neffort = "low"\n', "must not include effort"),
    ('[fast]\n[[fast.combos]]\nprovider = "x"\nmodel = "m"\neffort = "low"\nspeed = "fast"\n', "unknown key speed"),
    ('[fast]\n[[fast.combos]]\nprovider = "x"\nmodel = "m"\neffort = "low"\nservice_tier = ""\n',
     "service_tier must be a non-empty string"),
    ('[Fast]\n[[Fast.combos]]\nprovider = "x"\nmodel = "m"\neffort = "low"\n', "a model type name is"),
    ('fast = "x"\n', "fast must be a table"),
    ('[fast]\ncolor = "red"\n', "unknown key color"),
])
def test_spawn_refuses_a_bad_model_types_file(fake_spawn, text, message):
    fake_spawn.model_types(text)
    assert_rejected(fake_spawn.run("reviewer", "--dry-run"), message)
    assert fake_spawn.calls == []


def test_spawn_falls_back_to_the_next_combo_when_herdr_agent_start_fails(fake_spawn):
    fake_spawn.model_types(TYPES)
    fake_spawn.personas(persona(model_type="sharp"))
    fake_spawn.replies(table=TYPES_TABLE, overrides={"herdr agent start": [START_FAILED, START_FAILED, {"stdout": "{}"}]})
    result = fake_spawn.run("reviewer")
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert [a["result"] for a in out["attempts"]] == ["start failed (exit 1)", "start failed (exit 1)", "started"]
    assert [(a["type"], a["model"]) for a in out["attempts"]] == [
        ("persona", "claude-opus-5"), ("sharp", "claude-sonnet-5-5"), ("sharp", "grok-4.7"),
    ]
    assert out["combo"]["model"] == "grok-4.7" and out["command"][4] == "grok-4.7"
    assert [call[1:3] for call in fake_spawn.herdr_calls()] == [
        ["tab", "create"], ["agent", "start"], ["pane", "read"], ["tab", "close"],
    ] * 2 + [["tab", "create"], ["agent", "start"]]
    names = [call[3] for call in fake_spawn.herdr_calls() if call[1:3] == ["agent", "start"]]
    assert len(set(names)) == 3 and all(re.fullmatch(r"reviewer-[0-9a-f]{4}", n) for n in names)
    assert result.stderr.count("trying the next combo") == 2


def test_spawn_api_error_after_the_prompt_closes_the_tab_and_falls_back(fake_spawn):
    fake_spawn.model_types(TYPES)
    fake_spawn.personas(persona(model_type="sharp"))
    fake_spawn.replies(table=TYPES_TABLE, overrides={"herdr agent get": [
        agent_info("idle", {"sparks_run": "0:ready"}),
        agent_info("idle"),  # real herdr may publish idle before sparks metadata
        agent_info("blocked", {"sparks_run": "1:error", "sparks_api_error": "401 invalid x-api-key"}),
        agent_info("idle", {"sparks_run": "0:ready"}), agent_info("idle", {"sparks_run": "1:ok"}),
    ]})
    result = fake_spawn.run("reviewer", "--prompt", "/skill:spark-verification PR 91", "--watch", "20")
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert [a["result"] for a in out["attempts"]] == [
        "api error (401 invalid x-api-key, status blocked)", "started",
    ]
    assert out["combo"]["model"] == "claude-sonnet-5-5"
    prompts = [call for call in fake_spawn.herdr_calls() if call[1:3] == ["agent", "prompt"]]
    assert prompts[0] == [
        "herdr", "agent", "prompt", "w1:p9", "/skill:spark-verification PR 91", "--wait",
        "--until", "idle", "--until", "blocked", "--until", "done",
    ]
    assert len(prompts) == 2
    assert [call[1:3] for call in fake_spawn.herdr_calls()].count(["tab", "close"]) == 1


def test_spawn_blocked_without_the_api_error_token_is_an_approval_wait_not_a_failure(fake_spawn):
    fake_spawn.replies(overrides={"herdr agent get": [
        agent_info("idle", {"sparks_run": "0:ready"}), agent_info("blocked", {"sparks_run": "1:running"}),
    ]})
    result = fake_spawn.run("reviewer", "--prompt", "go", "--watch", "3.1")
    assert result.returncode == 1, result.stderr
    assert "approval block" in json.loads(result.stdout)["attempts"][-1]["result"]
    assert ["tab", "close"] not in [call[1:3] for call in fake_spawn.herdr_calls()]


def test_spawn_api_error_on_every_combo_exits_1_with_every_attempt(fake_spawn):
    fake_spawn.replies(overrides={"herdr agent get": [agent_info("idle", {"sparks_run": "0:ready"}),
        agent_info("blocked", {"sparks_run": "1:error", "sparks_api_error": "overloaded"})]})
    result = fake_spawn.run("reviewer", "--prompt", "go")
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["attempts"][0]["result"] == "api error (overloaded, status blocked)"
    assert out["attempts"][0]["closed"] is True
    assert result.stderr.endswith("sparks: every combo for model type fast failed\n")


def test_spawn_a_prompt_herdr_refuses_is_not_a_provider_api_error(fake_spawn):
    fake_spawn.model_types(TYPES)
    fake_spawn.personas(persona(model_type="sharp"))
    fake_spawn.replies(table=TYPES_TABLE, overrides={"herdr agent prompt": [
        {"code": 1, "stderr": "agent exited\n"}, {"stdout": "{}"},
    ]})
    result = fake_spawn.run("reviewer", "--prompt", "go")
    assert result.returncode == 1, result.stderr
    out = json.loads(result.stdout)
    assert result.returncode == 1
    assert len(out["attempts"]) == 1
    assert "prompt submission failed" in out["attempts"][0]["result"]
    assert out["left_open"] == ["w1:t9"]
    assert ["tab", "close"] not in [c[1:3] for c in fake_spawn.herdr_calls()]


def test_spawn_without_a_prompt_never_prompts_or_watches(fake_spawn):
    fake_spawn.replies(overrides={"herdr agent get": agent_info("blocked", {"sparks_api_error": "x"})})
    assert fake_spawn.run("reviewer").returncode == 0
    assert [call[1:3] for call in fake_spawn.herdr_calls()] == [["tab", "create"], ["agent", "start"]]


def test_spawn_dry_run_shows_the_prompt_and_watch_window(fake_spawn):
    plan = fake_spawn.plan("reviewer", "--prompt", "--start here", "--watch", "12")
    assert (plan["prompt"], plan["watch_ms"]) == ("--start here", 12000)
    assert fake_spawn.plan("reviewer", "--prompt", "go")["watch_ms"] == 60000
    result = fake_spawn.run("reviewer", "--dry-run", "--prompt", "two\nlines")
    assert_rejected(result, "--prompt must be one non-empty line")


# the shipped personas and model types


DEFAULTS_TABLE = """\
provider      model                context  max-out  thinking  images
anthropic     claude-opus-5-5      1M       128K     yes       yes
anthropic     claude-sonnet-5-5    1M       128K     yes       yes
anthropic     claude-haiku-5-5     1M       128K     yes       yes
openai-codex  gpt-6.1-sol          272K     128K     yes       yes
openai-codex  gpt-5.3-codex-spark  128K     128K     yes       no
xai           grok-4.7             500K     500K     yes       yes
xai           grok-4.3             1M       30K      yes       yes
"""


def test_spawn_default_personas_plan_without_a_project_file(fake_spawn):
    fake_spawn.config.unlink()
    fake_spawn.replies(table=DEFAULTS_TABLE)
    plans = {name: fake_spawn.plan(name) for name in ("spec-writer", "implementer", "reviewer")}
    for name, plan in plans.items():
        assert Path(plan["config"]) == ROOT / "defaults" / "agents.toml"
        assert all(step["available"] for step in plan["chain"]), plan["chain"]
        assert len(plan["chain"]) == 7  # every shipped combo, once
        assert sparks_prompt(name) in plan["command"]
    reviewer = plans["reviewer"]["command"]
    assert plans["reviewer"]["model_type"] == "powerful"
    assert reviewer[1:7] == ["--provider", "anthropic", "--model", "claude-opus-5-5", "--thinking", "high"]
    assert reviewer[7:12] == [
        "--exclude-tools", "edit,write", "--no-skills", "--skill", str(ROOT / "skills" / "spark-verification"),
    ]
    writer = plans["spec-writer"]["command"]
    assert writer[7:10] == ["--no-skills", "--skill", str(ROOT / "skills" / "sparks-postcall")]
    implementer = plans["implementer"]["command"]
    assert plans["implementer"]["model_type"] == "value"
    assert implementer[1:7] == ["--provider", "anthropic", "--model", "claude-sonnet-5-5", "--thinking", "medium"]
    assert implementer[7:10] == ["--no-skills", "-e", EXTENSION]


def test_spawn_project_persona_replaces_the_default_of_that_name(fake_spawn):
    fake_spawn.personas(persona("implementer", effort="low"))
    plan = fake_spawn.plan("implementer")
    assert Path(plan["config"]) == fake_spawn.config
    assert plan["command"][1:7] == ["--provider", "anthropic", "--model", "claude-opus-5", "--thinking", "low"]


def test_spawn_shipped_model_types_are_value_powerful_and_fast():
    types, files = cli._model_types(Path(os.sep))
    assert files == [ROOT / "defaults" / "model-types.toml"]
    assert {"value", "powerful", "fast"} <= set(types)
    for value in types.values():
        assert value["combos"] and value["fallback"]


# the api-error pi extension




@pytest.mark.parametrize("policy", [{"allowed_mcp": ["docs"]}, {"forbidden_mcp": ["private"]}, {"allowed_mcp": []}])
@pytest.mark.parametrize("pattern", ["*", "read*", "?", "m*?"])
def test_spawn_selective_mcp_refuses_tool_wildcards(fake_spawn, policy, pattern):
    fake_spawn.personas(persona(allowed_tools=["read", pattern], **policy))
    assert_rejected(fake_spawn.run("reviewer", "--dry-run"), "patterns containing * or ? bypass selective MCP")
    assert fake_spawn.herdr_calls() == []


def installed_pi_core():
    # Read-only managed install, never change the user's pi resources.
    install = INSTALLED_PI_DIR / "install"
    current = install / "current-version"
    if not current.is_file():
        pytest.skip("needs the managed pi install for its real tool-selection oracle")
    core = install / "releases" / current.read_text().strip() / "node_modules/@earendil-works/pi-coding-agent/dist/core"
    if not (core / "agent-session.js").is_file() or shutil.which("node") is None:
        pytest.skip("needs node and installed pi's AgentSession")
    return core


@pytest.mark.parametrize("policy", ["allowed", "forbidden"])
@pytest.mark.parametrize("opt_in", [False, True])
def test_spawn_mcp_policy_with_real_pi_selection(fake_spawn, tmp_path, policy, opt_in):
    core = installed_pi_core()
    allowed = ["read", "codemode"] + (["read_mcp_resource"] if opt_in else [])
    fake_spawn.personas(persona(allowed_tools=allowed, **{f"{policy}_mcp": ["docs" if policy == "allowed" else "private"]}))
    command = fake_spawn.plan("reviewer")["command"]
    driver = tmp_path / "selection.mjs"
    driver.write_text(r'''
const [core, raw] = process.argv.slice(2);
const {AgentSession} = await import(`${core}/agent-session.js`);
const {createToolNameMatcher} = await import(`${core}/mcp-servers.js`);
const args = JSON.parse(raw);
const names = args[args.indexOf("--tools") + 1].split(",");
const excluded = args[args.indexOf("--exclude-tools") + 1].split(",");
const session = Object.create(AgentSession.prototype);
session._allowedTools = createToolNameMatcher(names);
session._excludedTools = createToolNameMatcher(excluded);
session._allowlistFiltersMcp = names.some(n => n.startsWith("mcp__"));
const tools = ["read", "codemode", "mcp__docs__lookup", "mcp__private__delete",
  "list_mcp_resources", "list_mcp_resource_templates", "read_mcp_resource"];
console.log(JSON.stringify(Object.fromEntries(tools.map(n => [n, session._isAllowedTool(n)]))));
''')
    result = subprocess.run([shutil.which("node"), str(driver), core.as_uri(), json.dumps(command)],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    actual = json.loads(result.stdout)
    assert actual == {"read": True, "codemode": True, "mcp__docs__lookup": True,
                      "mcp__private__delete": False, "list_mcp_resources": False,
                      "list_mcp_resource_templates": False, "read_mcp_resource": opt_in}


@pytest.mark.parametrize("stream", ["stderr", "stdout"])
def test_spawn_rejected_approval_prompt_preserves_tab_without_fallback(fake_spawn, stream):
    fake_spawn.model_types(TYPES)
    fake_spawn.personas(persona(model_type="sharp"))
    fake_spawn.replies(table=TYPES_TABLE, overrides={
        "herdr agent prompt": [{"code": 1, stream: json.dumps({"error": {
            "code": "agent_blocked", "message": "waiting for approval"}})}, {"stdout": "{}"}],
        "herdr agent get": [agent_info("idle", {"sparks_run": "0:ready"}), agent_info("blocked")],
    })
    result = fake_spawn.run("reviewer", "--prompt", "go")
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert "approval block (agent_blocked)" in out["attempts"][0]["result"]
    assert out["left_open"] == ["w1:t9"]
    assert len(out["attempts"]) == 1
    calls = [c[1:3] for c in fake_spawn.herdr_calls()]
    assert calls.count(["agent", "start"]) == 1 and ["tab", "close"] not in calls


def test_spawn_failed_close_stops_before_an_available_successful_combo(fake_spawn):
    fake_spawn.model_types(TYPES)
    fake_spawn.personas(persona(model_type="sharp"))
    fake_spawn.replies(table=TYPES_TABLE, overrides={
        "herdr agent start": [START_FAILED, {"stdout": "{}"}],
        "herdr tab close": {"code": 1, "stderr": "nope"},
    })
    result = fake_spawn.run("reviewer")
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["left_open"] == ["w1:t9"] and len(out["attempts"]) == 1
    assert out["attempts"][0]["closed"] is False
    assert sum(c[1:3] == ["agent", "start"] for c in fake_spawn.herdr_calls()) == 1


@pytest.mark.parametrize("info", [agent_info("idle"), agent_info("idle", {"sparks_run": "0:ok"}),
    agent_info("working", {"sparks_run": "1:running"}),
    agent_info("idle", {"sparks_run": "1:error"}), {"code": 1, "stderr": "metadata unavailable"}])
def test_spawn_unknown_or_stale_outcome_is_not_silent_success(fake_spawn, info):
    fake_spawn.replies(overrides={"herdr agent get": [agent_info("idle", {"sparks_run": "0:ready"}), info]})
    result = fake_spawn.run("reviewer", "--prompt", "go", "--watch", "3.1")
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert "failure to confirm" in out["attempts"][0]["result"]
    assert out["left_open"] == ["w1:t9"]
    assert ["tab", "close"] not in [c[1:3] for c in fake_spawn.herdr_calls()]


def test_spawn_delayed_baseline_and_stale_previous_error_are_reconciled(fake_spawn):
    fake_spawn.replies(overrides={"herdr agent get": [
        agent_info("idle"),
        agent_info("idle", {"sparks_run": "7:ok"}),
        agent_info("blocked", {"sparks_run": "7:error", "sparks_api_error": "stale"}),
        agent_info("idle", {"sparks_run": "8:ok"}),
    ]})
    result = fake_spawn.run("reviewer", "--prompt", "go")
    assert result.returncode == 0, result.stderr
    assert len(json.loads(result.stdout)["attempts"]) == 1
    assert sum(c[1:3] == ["agent", "get"] for c in fake_spawn.herdr_calls()) == 4
    assert ["tab", "close"] not in [c[1:3] for c in fake_spawn.herdr_calls()]


def test_spawn_approval_without_even_a_baseline_preserves_the_tab(fake_spawn):
    fake_spawn.replies(overrides={"herdr agent get": agent_info("blocked")})
    result = fake_spawn.run("reviewer", "--prompt", "go")
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert "approval block" in out["attempts"][0]["result"]
    assert out["left_open"] == ["w1:t9"]
    assert ["tab", "close"] not in [c[1:3] for c in fake_spawn.herdr_calls()]


EXTENSION_DRIVER = r"""
import net from "node:net";
import {EventEmitter} from "node:events";
const [extension, herdr, socketPath, order, fail] = process.argv.slice(2);
let tokens = {};
const history = [];
const emitted = [];
const received = [];
const server = net.createServer(socket => {
  let buffer = "";
  socket.on("data", data => {
    buffer += data.toString();
    if (!buffer.includes("\n")) return;
    const request = JSON.parse(buffer.split("\n")[0]);
    received.push(request);
    const metadata = request.method === "pane.report_metadata";
    setTimeout(() => {
      if (metadata && !fail) Object.assign(tokens, request.params.tokens);
      history.push([metadata ? "metadata" : request.params.state, {...tokens}]);
      socket.write(JSON.stringify({id: request.id, ...(metadata && fail ?
        {error: {message: "synthetic metadata rejection"}} : {result: {type: "ok"}})}) + "\n");
    }, metadata ? 150 : 0);
  });
});
await new Promise(resolve => server.listen(socketPath, resolve));
process.env.HERDR_ENV = "1";
process.env.HERDR_SOCKET_PATH = socketPath;
process.env.HERDR_PANE_ID = "w1:p9";
const handlers = {};
const events = new EventEmitter();
events.on("herdr:blocked", data => emitted.push([data, {...tokens}]));
const pi = {on: (name, handler) => (handlers[name] ??= []).push(handler), events};
const module = await import(extension);
const managed = await import(herdr);
for (const init of order === "herdr-first" ? [managed.default, module.default] : [module.default, managed.default]) init(pi);
const ctx = {mode: "tui", isIdle: () => idle};
let idle = true;
const fire = async (name, event = {}) => {for (const h of handlers[name] ?? []) await h(event, ctx);};
await fire("session_start");
idle = false;
await fire("agent_start");
await fire("message_end", {message: {role: "assistant", stopReason: "error", provider: "custom",
  errorMessage: "HTTP 401 Incorrect API key provided: demo-secret-1234"}});
idle = true;
await fire("agent_settled");
await new Promise(resolve => setTimeout(resolve, 60));
const afterError = {tokens: {...tokens}, emitted: emitted.slice(), history: history.slice()};
idle = false;
await fire("agent_start");
await fire("message_end", {message: {role: "assistant", stopReason: "stop"}});
idle = true;
await fire("agent_settled");
await new Promise(resolve => setTimeout(resolve, 60));
const afterSuccess = {...tokens};
idle = false;
await fire("agent_start");
idle = true;
await fire("agent_settled", {aborted: true});
const redacted = [
  "Incorrect API key provided: demo-secret-1234", "token=x", "Bearer a", "Authorization: Basic xy",
  'custom provider: key="q"', "x-api-key: z", "token: short value with spaces", "sk-abc", "A".repeat(40),
  "overloaded " + "!".repeat(600), "token: 401", 'access_token="short-secret"', 'apiKey: v'
].map(errorMessage => module.apiError({role: "assistant", stopReason: "error", provider: "custom", errorMessage}));
server.close();
console.log(JSON.stringify({afterError, afterSuccess, tokens, emitted, received, redacted}));
"""


@pytest.mark.parametrize("order", ["herdr-first", "sparks-first"])
@pytest.mark.parametrize("fail", [False, True])
def test_extensions_delayed_metadata_both_load_orders_and_delivery_failure(tmp_path, order, fail):
    node = shutil.which("node")
    source = INSTALLED_PI_DIR / "extensions" / "herdr-agent-state.ts"
    if node is None or not source.is_file():
        pytest.skip("needs node and the real installed herdr extension (read-only source)")
    before = source.read_bytes()
    # Copy the real, unmodified managed extension; never edit the installed file.
    managed = tmp_path / "herdr-agent-state.ts"
    managed.write_bytes(before)
    managed.chmod(0o444)
    driver = tmp_path / "driver.mjs"
    driver.write_text(EXTENSION_DRIVER, encoding="utf-8")
    done = subprocess.run([node, str(driver), EXTENSION, str(managed), str(tmp_path / "herdr.sock"),
                           order, "fail" if fail else ""], capture_output=True, text=True, timeout=60)
    assert source.read_bytes() == before
    assert done.returncode == 0, done.stderr
    report = json.loads(done.stdout.strip().splitlines()[-1])
    if fail:
        assert report["emitted"] == []
        assert report["tokens"] == {}
        assert "completion metadata delivery failed; outcome unconfirmed" in done.stderr
    else:
        after = report["afterError"]
        assert after["tokens"]["sparks_run"] == "1:error"
        assert "HTTP 401 api error" in after["tokens"]["sparks_api_error"]
        assert "demo-secret-1234" not in json.dumps(report)
        # At blocked emission metadata has already been delivered/acknowledged.
        [(event, tokens)] = after["emitted"]
        assert event["active"] is True and tokens["sparks_run"] == "1:error"
        blocked = next(i for i, row in enumerate(after["history"]) if row[0] == "blocked")
        terminal = next(i for i, row in enumerate(after["history"]) if row[1].get("sparks_run") == "1:error")
        assert terminal < blocked
        if order == "herdr-first":
            assert any(state == "idle" and tokens.get("sparks_run") == "1:running" for state, tokens in after["history"])
        assert report["afterSuccess"] == {"sparks_run": "2:ok", "sparks_api_error": None}
        assert report["tokens"] == {"sparks_run": "3:aborted", "sparks_api_error": None}
        assert report["emitted"][1][0] == {"active": False}
    assert report["redacted"] == ["custom api error: model request failed"] * 13


# Drive the installed AgentSession's logical-run/retry lifecycle with the real
# Agent (and thus runAgentLoop/runAgentLoopContinue), synthetic streams only.
LOGICAL_RUN_DRIVER = r"""
import net from "node:net";
import {EventEmitter} from "node:events";
const [extension, core, socketPath, scenario, diagnostic] = process.argv.slice(2);
const {AgentSession} = await import(core + "/agent-session.js");
const packages = new URL("../../../", core + "/");
const {Agent} = await import(new URL("pi-agent-core/dist/agent.js", packages));
const {AssistantMessageEventStream} = await import(new URL("pi-ai/dist/utils/event-stream.js", packages));
let tokens = {};
const markers = [], labels = [], lifecycle = [], retryEvents = [];
const server = net.createServer(socket => {
  let buffer = "";
  socket.on("data", data => {
    buffer += data.toString();
    if (!buffer.includes("\n")) return;
    const request = JSON.parse(buffer.split("\n")[0]);
    Object.assign(tokens, request.params.tokens);
    markers.push(tokens.sparks_run);
    socket.write(JSON.stringify({id: request.id, result: {type: "ok"}}) + "\n");
  });
});
await new Promise(resolve => server.listen(socketPath, resolve));
process.env.HERDR_ENV = "1";
process.env.HERDR_SOCKET_PATH = socketPath;
process.env.HERDR_PANE_ID = "w1:p9";
const handlers = {};
const events = new EventEmitter();
events.on("herdr:blocked", data => labels.push(data));
const fire = async event => {
  lifecycle.push(event.type);
  for (const h of handlers[event.type] ?? []) await h(event, {mode: "tui"});
};
const module = await import(extension);
module.default({on: (name, h) => (handlers[name] ??= []).push(h), events});
await fire({type: "session_start"});
const model = {id: "synthetic", provider: "custom", api: "synthetic", contextWindow: 100000};
let calls = 0, nextRun = false;
const agent = new Agent({initialState: {model, tools: []}, streamFn: () => {
  calls++;
  const error = !nextRun && (scenario === "retry-exhausted" || (scenario === "retry-success" && calls === 1));
  const message = {role: "assistant", provider: "custom", model: "synthetic", api: "synthetic",
    content: [], stopReason: error ? "error" : "stop", timestamp: Date.now(),
    usage: {input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
      cost: {input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0}},
    ...(error ? {errorMessage: diagnostic} : {})};
  const stream = new AssistantMessageEventStream();
  stream.push(error ? {type: "error", reason: "error", error: message} : {type: "done", reason: "stop", message});
  return stream;
}});
const session = Object.create(AgentSession.prototype);
// Replace persistence/prompt construction and compaction with an in-memory
// transcript. _startRun, _handlePostAgentRun, _prepareRetry and settlement are
// installed pi code, not a hand-paired start/settled event simulation.
Object.assign(session, {agent, _retryAttempt: 0, _lastAssistantToolResults: [],
  _pendingToolNames: new Set(), _deferredSettledActions: [],
  settingsManager: {getRetrySettings: () => ({enabled: true, maxRetries: 1, baseDelayMs: 0, maxDelayMs: 0})},
  _extensionRunner: {emit: fire},
  _prepareRun: async () => [{role: "user", content: [{type: "text", text: "synthetic task"}], timestamp: Date.now()}],
  _recordSelection: () => {}, _flushPendingBashMessages: () => {}, _flushPendingCustomMessages: () => {},
  _resolveIdleWaitIfIdle: () => {}, _modelForMessage: () => model,
  _checkCompaction: async () => false,
  _omitRecoveryAttempt: message => {agent.state.messages = agent.state.messages.filter(m => m !== message);},
  _emit: event => {if (event.type.startsWith("auto_retry")) retryEvents.push({type: event.type, success: event.success});},
  _runBeforeSettleBoundary: async () => false,
});
let queued = false;
agent.subscribe(async event => {
  await fire(event);
  if (event.type === "message_end" && event.message.role === "assistant") {
    session._lastAssistantMessage = event.message;
    if (event.message.stopReason !== "error" && session._retryAttempt > 0) {
      session._emit({type: "auto_retry_end", success: true});
      session._retryAttempt = 0;
    }
  }
  // Work queued at agent_end needs another low-level loop before settlement,
  // just like recovery or an agent_before_settle continuation.
  if (event.type === "agent_end" && scenario === "continuation" && !queued) {
    queued = true;
    agent.followUp({role: "user", content: [{type: "text", text: "continue"}], timestamp: Date.now()});
  }
});
await session._startRun({});
const terminal = {...tokens}, firstMarkers = markers.slice(), firstLifecycle = lifecycle.slice();
nextRun = true;
await session._startRun({});
server.close();
console.log(JSON.stringify({terminal, firstMarkers, firstLifecycle, markers, labels, tokens, calls, retryEvents}));
"""


SECRET_DIAGNOSTICS = [
    "HTTP 503 demo-secret-1234 is not a valid API key",
    "HTTP 503 Authentication failed for credential: demo-secret-1234",
    "HTTP 503 password demo-secret-1234 was rejected",
    "HTTP 503 client-secret demo-secret-1234 was rejected",
    "HTTP 503 Unable to reach https://user:demo-secret-1234@example.invalid/v1",
    "HTTP 503 Unlabelled diagnostic demo-secret-1234",  # no heuristic needed
]


@pytest.mark.parametrize(("scenario", "diagnostic"), [
    ("retry-success", SECRET_DIAGNOSTICS[0]),
    ("continuation", "unused"),
    *[("retry-exhausted", text) for text in SECRET_DIAGNOSTICS],
])
def test_spawn_actual_pi_logical_run_and_safe_error_fallback(fake_spawn, tmp_path, scenario, diagnostic):
    core = installed_pi_core()
    driver = tmp_path / "logical-run.mjs"
    driver.write_text(LOGICAL_RUN_DRIVER, encoding="utf-8")
    done = subprocess.run([shutil.which("node"), str(driver), EXTENSION, core.as_uri(),
                           str(tmp_path / "logical.sock"), scenario, diagnostic],
                          capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    report = json.loads(done.stdout.strip().splitlines()[-1])
    error = scenario == "retry-exhausted"
    outcome = "error" if error else "ok"
    assert report["firstMarkers"] == ["0:ready", "1:running", "1:running", f"1:{outcome}"]
    assert report["markers"][-2:] == ["2:running", "2:ok"]
    assert report["calls"] == 3
    assert report["firstLifecycle"].count("agent_start") == 2
    assert report["firstLifecycle"].count("agent_end") == 2
    assert report["firstLifecycle"].count("agent_settled") == 1
    assert report["tokens"] == {"sparks_run": "2:ok", "sparks_api_error": None}
    if error:
        safe = "custom HTTP 503 api error: model request failed"
        assert report["terminal"]["sparks_api_error"] == safe
        assert report["labels"] == [{"active": True, "label": "sparks:api-error: " + safe}, {"active": False}]
        assert report["retryEvents"][-1] == {"type": "auto_retry_end", "success": False}
    else:
        assert report["terminal"]["sparks_api_error"] is None
        assert report["labels"] == []  # transient diagnostics never leave pi
    fake_spawn.model_types(TYPES)
    fake_spawn.personas(persona(model_type="sharp"))
    infos = [agent_info("idle", {"sparks_run": "0:ready"}),
             agent_info("blocked" if error else "idle", report["terminal"])]
    if error:
        infos += [agent_info("idle", {"sparks_run": "0:ready"}), agent_info("idle", {"sparks_run": "1:ok"})]
    fake_spawn.replies(table=TYPES_TABLE, overrides={"herdr agent get": infos})
    result = fake_spawn.run("reviewer", "--prompt", "go", "--watch", "20")
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert len(out["attempts"]) == (2 if error else 1)
    assert out["attempts"][-1]["result"] == "started"
    assert sum(c[1:3] == ["tab", "close"] for c in fake_spawn.herdr_calls()) == int(error)
    if error:
        assert out["combo"]["model"] == "claude-sonnet-5-5"
        assert safe in out["attempts"][0]["result"] and safe in result.stderr
    # Covers shared tokens, blocked labels, extension streams, CLI stderr and
    # attempts JSON. The original diagnostic is never an orchestration payload.
    assert "demo-secret-1234" not in done.stdout + done.stderr + result.stdout + result.stderr


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

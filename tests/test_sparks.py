# /// script
# requires-python = ">=3.11"
# dependencies = ["jsonschema>=4.18", "pytest>=8", "xxhash>=3.4"]
# ///

"""Tests for bin/sparks. Run them with ``uv run tests/test_sparks.py``."""

import errno
import importlib.machinery
import importlib.util
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import xxhash
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "sparks"
sys.path.insert(0, str(ROOT))

import spark_id  # noqa: E402

posix = pytest.mark.skipif(os.name != "posix", reason="needs POSIX modes, signals, or flock")


def _import_cli():
    """bin/sparks has no .py suffix, so in-process tests load it by path."""
    loader = importlib.machinery.SourceFileLoader("sparks_cli", str(BIN))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    return module


cli = _import_cli()


def spark(question="Why is main protected?", answer="Every merge must pass CI first.", spark_type="S"):
    return {
        "type": spark_type,
        "question": question,
        "answer": answer,
    }


def record_id(record):
    return spark_id.Spark(record["question"], record["answer"], record["type"]).id


def stored(*records):
    """records as sparks stores them: with the id it assigns on add."""
    return [{**record, "id": record_id(record)} for record in records]


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


def add(path, record, *, cwd=None, **kwargs):
    text = record if isinstance(record, str) else json.dumps(record)
    return sparks(
        "entry", "add", "--path", str(path), "--json", text, cwd=cwd or path.parent, **kwargs
    )


def command(path, record):
    """The argv of a bin/sparks run that adds record to path."""
    args = ["entry", "add", "--path", str(path), "--json", json.dumps(record)]
    return [sys.executable, str(BIN), *args]


def run_main(path, record):
    """In-process run, so tests can break os functions halfway through a write."""
    return cli.main(["entry", "add", "--path", str(path), "--json", json.dumps(record)])


def seed(path, records):
    """Write a spark file the way sparks does, ids included, and return its bytes."""
    path.write_bytes((json.dumps(stored(*records), ensure_ascii=False, indent=2) + "\n").encode())
    return path.read_bytes()


def others(directory, name="sparks.json"):
    """Everything in directory except the spark file: leftover temp or lock files."""
    return sorted(p.name for p in directory.iterdir() if p.name != name)


def assert_rejected(result, message, code=1):
    assert result.returncode == code
    assert result.stdout == ""
    assert result.stderr.startswith("sparks: "), result.stderr
    assert result.stderr.count("\n") == 1, result.stderr  # one line, no traceback
    assert message in result.stderr


# create, append, default path


def test_creates_a_missing_file_with_the_record(tmp_path):
    path = tmp_path / "sparks.json"
    result = add(path, FIRST)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"added {record_id(FIRST)} to {path}\n"
    assert result.stderr == ""
    assert json.loads(path.read_bytes()) == stored(FIRST)
    assert others(tmp_path) == []


def test_output_matches_the_repo_example_byte_for_byte(tmp_path):
    example = ROOT / "spark.json"
    path = tmp_path / "sparks.json"
    (record,) = json.loads(example.read_bytes())
    assert record.pop("id") == record_id(record) == "e91d4755e9dea051"  # pins XXH3-64
    assert add(path, record).returncode == 0
    # A Windows checkout may have turned the example's line endings into CRLF.
    assert path.read_bytes() == example.read_bytes().replace(b"\r\n", b"\n")


def test_default_path_is_sparks_json_in_the_working_directory(tmp_path):
    for record in (FIRST, SECOND):  # creates, then appends
        result = sparks("entry", "add", "--json", json.dumps(record), cwd=tmp_path)
        assert result.returncode == 0, result.stderr
        assert result.stdout == f"added {record_id(record)} to sparks.json\n"
    assert json.loads((tmp_path / "sparks.json").read_bytes()) == stored(FIRST, SECOND)
    assert others(tmp_path) == []


def test_relative_path_resolves_against_the_working_directory(tmp_path):
    (tmp_path / "docs").mkdir()
    result = sparks(
        "entry", "add", "--path", "docs/notes.json", "--json", json.dumps(FIRST), cwd=tmp_path
    )
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / "docs" / "notes.json").read_bytes()) == stored(FIRST)


def test_appends_after_existing_records_and_keeps_them(tmp_path):
    path = tmp_path / "sparks.json"
    # Hand-written: compact, with keys in a different order.
    hand_written = {key: stored(FIRST)[0][key] for key in ("id", "answer", "question", "type")}
    path.write_bytes(json.dumps([hand_written]).encode())
    third = spark("Is a third record kept in order?", "Yes, at the end.")
    assert add(path, SECOND).returncode == 0
    assert add(path, third).returncode == 0
    records = json.loads(path.read_bytes())
    assert records == stored(FIRST, SECOND, third)
    assert list(records[0]) == ["id", "answer", "question", "type"]


def test_new_record_is_stored_in_schema_key_order(tmp_path):
    path = tmp_path / "sparks.json"
    shuffled = json.dumps({key: FIRST[key] for key in ("answer", "question", "type")})
    assert add(path, shuffled).returncode == 0
    assert list(json.loads(path.read_bytes())[0]) == ["type", "question", "answer", "id"]


def test_non_ascii_is_kept_verbatim_and_hashed_by_the_spec_rule(tmp_path):
    question = "¿Por qué “verbatim”?"
    answer = "Naïve café prose — 日本語 🙂, kept as written."
    preimage = json.dumps(
        {"answer": answer, "question": question, "type": "S"},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    record = {"type": "S", "question": question, "answer": answer}
    assert record_id(record) == xxhash.xxh3_64_hexdigest(preimage.encode("utf-8"))
    path = tmp_path / "sparks.json"
    result = add(path, record)
    assert result.returncode == 0, result.stderr
    text = path.read_bytes().decode("utf-8")
    assert question in text and answer in text  # no \u escapes
    assert json.loads(text) == stored(record)


@pytest.mark.parametrize("spark_type", ["S", "R"])
def test_exact_question_replaces_whole_record_in_place(tmp_path, spark_type):
    path = tmp_path / "sparks.json"
    third = spark("Another question?", "Another answer.")
    seed(path, [SECOND, FIRST, third])
    revised = spark(FIRST["question"], "Every merge must pass CI and one review.", spark_type)
    result = add(path, revised)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"added {record_id(revised)} to {path}\n"
    assert json.loads(path.read_bytes()) == stored(SECOND, revised, third)
    assert record_id(revised) != record_id(FIRST)
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
    assert json.loads(path.read_bytes()) == stored(original, incoming)


def test_json_escape_spelling_does_not_change_question_identity(tmp_path):
    path = tmp_path / "sparks.json"
    original = spark("Café?")
    seed(path, [original])
    revised = spark(original["question"], "Updated.")
    assert add(path, json.dumps(revised, ensure_ascii=True)).returncode == 0
    assert json.loads(path.read_bytes()) == stored(revised)


@pytest.mark.parametrize("incoming", [FIRST, spark(FIRST["question"], "Updated.")])
def test_multiple_exact_matches_are_refused_without_writing(tmp_path, incoming):
    path = tmp_path / "sparks.json"
    before = seed(path, [FIRST, SECOND, spark(FIRST["question"], "Old answer.", "R")])
    assert_rejected(add(path, incoming), "2 records have the exact question")
    assert path.read_bytes() == before
    assert others(tmp_path) == []


def test_failed_replacement_keeps_old_record(tmp_path, monkeypatch, capsys):
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
def test_concurrent_adds_of_same_question_leave_one_record(tmp_path):
    path = tmp_path / "sparks.json"
    records = [spark(FIRST["question"], f"Revision {i}") for i in range(10)]
    processes = [subprocess.Popen(command(path, record), stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE) for record in records]
    for process in processes:
        stdout, stderr = process.communicate(timeout=30)
        assert process.returncode == 0, stderr
        assert stdout.startswith(b"added ")
    written = json.loads(path.read_bytes())
    assert len(written) == 1
    assert written[0] in stored(*records)
    assert others(tmp_path) == []


def test_written_file_passes_spark_id_and_the_schema(tmp_path):
    path = tmp_path / "sparks.json"
    for record in (FIRST, SECOND):
        assert add(path, record).returncode == 0
    assert spark_id.main(["spark_id.py", str(path)]) == 0
    schema = json.loads((ROOT / "spark.schema.json").read_bytes())
    Draft202012Validator(schema).validate(json.loads(path.read_bytes()))


@posix
def test_a_file_name_near_the_length_limit_works(tmp_path):
    path = tmp_path / ("s" * 246 + ".json")  # 251 bytes; most file systems allow 255
    assert add(path, FIRST).returncode == 0
    assert json.loads(path.read_bytes()) == stored(FIRST)
    assert others(tmp_path, path.name) == []


# rejections: --json

DROP = object()


def _payload(**changes):
    record = {**FIRST, **changes}
    return json.dumps({key: value for key, value in record.items() if value is not DROP})


def _raw_question(raw):
    """A payload whose question is the raw JSON text raw."""
    return _payload(question="RAW").replace('"RAW"', raw)


BAD_INPUT = [
    pytest.param("{", "--json: invalid JSON: ", id="truncated"),
    pytest.param("", "--json: invalid JSON: ", id="empty"),
    pytest.param(_payload() + " x", "--json: invalid JSON: Extra data", id="trailing-data"),
    pytest.param(_raw_question("NaN"), "--json: NaN is not valid JSON", id="nan"),
    pytest.param(_raw_question("9" * 5000), "--json: number has too many digits", id="huge-int"),
    pytest.param(json.dumps([FIRST]), "--json: expected one JSON object", id="array"),
    pytest.param('"text"', "--json: expected one JSON object", id="string"),
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
        "--json: type: 'spark' is not one of ['S', 'P', 'A', 'R', 'K']",
        id="wrong-type",
    ),
    pytest.param(
        _payload(type="SPARK"),
        "--json: type: 'SPARK' is not one of ['S', 'P', 'A', 'R', 'K']",
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
        _payload(id=record_id(FIRST)),
        "--json: id is assigned by sparks on add; leave it out",
        id="id-not-accepted",
    ),
    pytest.param(
        _payload(id=None), "--json: id is assigned by sparks on add; leave it out", id="id-null"
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
    payload = b'{"type": "S", "question": "\xff", "answer": "a"}'
    result = subprocess.run(
        [sys.executable, str(BIN), "entry", "add", "--path", str(path), "--json", payload],
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
    pytest.param(b"[1]", "[0]: 1 is not of type 'object'", id="not-a-record"),
    pytest.param(b"[NaN]", "NaN is not valid JSON", id="nan"),
    pytest.param(json.dumps([FIRST]).encode(), "[0]: 'id' is a required property", id="no-id"),
    pytest.param(
        json.dumps([{**FIRST, "id": "0" * 16}]).encode(),
        "stored id does not match the record",
        id="wrong-id",
    ),
    pytest.param(
        json.dumps([{**FIRST, "id": record_id(FIRST).upper()}]).encode(),
        "[0].id: '" + record_id(FIRST).upper() + "' does not match '^[0-9a-f]{16}$'",
        id="uppercase-id",
    ),
    pytest.param(json.dumps(stored(FIRST, FIRST)).encode(), "duplicate id", id="duplicate-record"),
    pytest.param(
        json.dumps(stored(FIRST))[:-2].encode() + b', "answer": "again"}]',
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
        json.dumps(
            [{**spark(f"Q{i}?", "A."), "type": "x", "id": "0" * 16} for i in range(10)]
        ).encode()
    )
    result = add(path, FIRST)
    assert_rejected(result, "[2].type: 'x' is not one of ['S', 'P', 'A', 'R', 'K']; and 7 more")
    assert result.stderr.count("is not one of") == 3
    huge = tmp_path / "package.json"  # an object, not a spark file
    huge.write_bytes(json.dumps({f"key{i}": "v" * 100 for i in range(10_000)}).encode())
    result = add(huge, FIRST)
    assert_rejected(result, "is not of type 'array'")
    assert len(result.stderr) < len(str(huge)) + 300


def test_identical_add_succeeds_without_rewriting(tmp_path):
    path = tmp_path / "sparks.json"
    path.write_text(json.dumps(stored(FIRST, SECOND)), encoding="utf-8")
    before = path.read_bytes()
    inode = path.stat().st_ino
    result = add(path, FIRST)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"added {record_id(FIRST)} to {path}\n"
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
    [[], ["entry"], ["entry", "add"], ["entry", "add", "--path", "x.json"], ["entry", "drop"]],
    ids=["no-command", "no-action", "no-json", "path-without-json", "unknown-action"],
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
    assert json.loads(shared.read_bytes()) == stored(FIRST, SECOND)


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
    argv = ["entry", "add", "--path", str(path), "--json", json.dumps(SECOND)]
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
    assert json.loads(path.read_bytes()) == stored(FIRST, SECOND)
    assert others(tmp_path) == [temp]


def test_invalid_new_content_never_replaces_the_file(tmp_path, monkeypatch, capsys):
    path = tmp_path / "sparks.json"
    before = seed(path, [FIRST])
    monkeypatch.setattr(cli, "render", lambda records: '[{"type": "S"}]\n')
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
    records = [spark(f"Question {i}?", f"Answer {i}.") for i in range(20)]
    children = [
        subprocess.Popen(
            [sys.executable, str(BIN), "entry", "add", "--json", json.dumps(record)],
            cwd=tmp_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for record in records
    ]
    assert [child.wait(timeout=120) for child in children] == [0] * len(records)
    written = json.loads((tmp_path / "sparks.json").read_bytes())
    assert sorted(written, key=lambda r: r["question"]) == sorted(
        stored(*records), key=lambda r: r["question"]
    )
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
    assert json.loads(path.read_bytes()) == stored(FIRST, SECOND)
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
    assert json.loads(path.read_bytes()) == stored(FIRST)


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
    assert json.loads(path.read_bytes()) == stored(FIRST)


def test_a_path_stdout_cannot_encode_is_escaped(tmp_path):
    path = tmp_path / "café.json"
    result = add(path, FIRST, env={"PYTHONIOENCODING": "ascii:strict"})
    shown = str(path).encode("ascii", "backslashreplace").decode("ascii")
    assert (result.returncode, result.stdout) == (0, f"added {record_id(FIRST)} to {shown}\n")
    assert json.loads(path.read_bytes()) == stored(FIRST)


# help and the uv entry point


def test_help_shows_the_usage_exit_codes_and_exact_replace_semantics(tmp_path):
    result = sparks("entry", "add", "--help", cwd=tmp_path)
    assert result.returncode == 0
    assert result.stdout.startswith("usage: sparks entry add [-h] [--path <path>] --json <json>\n")
    assert "exit status: 0 added or replaced; 1 refused, nothing written; 2 usage error; 3 written" in (
        result.stdout
    )
    assert "An exact question match replaces the entire record" in result.stdout
    assert "Multiple exact matches are" in result.stdout
    assert "An identical record succeeds without rewriting." in result.stdout


@posix
@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv on PATH")
def test_runs_as_an_executable_uv_script(tmp_path):
    result = subprocess.run(
        [str(BIN), "entry", "add", "--json", json.dumps(FIRST)],
        cwd=tmp_path,
        capture_output=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"added {record_id(FIRST)} to sparks.json\n"
    assert json.loads((tmp_path / "sparks.json").read_bytes()) == stored(FIRST)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-p", "no:cacheprovider", *sys.argv[1:]]))

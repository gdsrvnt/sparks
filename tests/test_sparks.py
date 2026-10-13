# /// script
# requires-python = ">=3.11"
# dependencies = ["jsonschema>=4.18", "pytest>=8"]
# ///

"""Tests for bin/sparks. Run them with ``uv run tests/test_sparks.py``."""

import errno
import hashlib
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
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "sparks"
ISSUE_21 = "https://github.com/gdsrvnt/sparks/issues/21"
sys.path.insert(0, str(ROOT))

import spark_id  # noqa: E402

posix = pytest.mark.skipif(os.name != "posix", reason="needs POSIX modes, symlinks, or signals")


def _import_cli():
    """bin/sparks has no .py suffix, so in-process tests load it by path."""
    loader = importlib.machinery.SourceFileLoader("sparks_cli", str(BIN))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    return module


cli = _import_cli()


def spark(question="Why is main protected?", answer="Every merge must pass CI first."):
    return {
        "type": "SPARK",
        "question": question,
        "answer": answer,
        "id": spark_id.Spark(question, answer).id,
    }


FIRST = spark()
SECOND = spark("Who reviews skill changes?", "Anyone who did not write them.")


def sparks(*args, cwd):
    """Run bin/sparks in a child process, the way a shell would."""
    return subprocess.run(
        [sys.executable, str(BIN), *args], cwd=cwd, capture_output=True, encoding="utf-8"
    )


def add(path, record, *, cwd=None):
    text = record if isinstance(record, str) else json.dumps(record)
    return sparks("entry", "add", "--path", str(path), "--json", text, cwd=cwd or path.parent)


def run_main(path, record):
    """In-process run, so tests can break os functions halfway through a write."""
    return cli.main(["entry", "add", "--path", str(path), "--json", json.dumps(record)])


def seed(path, records):
    """Write a spark file the way sparks does and return its bytes."""
    path.write_bytes((json.dumps(records, ensure_ascii=False, indent=2) + "\n").encode())
    return path.read_bytes()


def others(directory, name="sparks.json"):
    """Everything in directory except the spark file, such as leftover temp files."""
    return sorted(p.name for p in directory.iterdir() if p.name != name)


def assert_rejected(result, message):
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("sparks: "), result.stderr
    assert result.stderr.count("\n") == 1, result.stderr  # one line, no traceback
    assert message in result.stderr


# create, append, default path


def test_creates_a_missing_file_with_the_record(tmp_path):
    path = tmp_path / "sparks.json"
    result = add(path, FIRST)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"added {FIRST['id']} to {path}\n"
    assert result.stderr == ""
    assert json.loads(path.read_bytes()) == [FIRST]
    assert others(tmp_path) == []


def test_output_matches_the_repo_example_byte_for_byte(tmp_path):
    example = ROOT / "spark.json"
    path = tmp_path / "sparks.json"
    (record,) = json.loads(example.read_bytes())
    assert add(path, record).returncode == 0
    assert path.read_bytes() == example.read_bytes()


def test_default_path_is_sparks_json_in_the_working_directory(tmp_path):
    for record in (FIRST, SECOND):  # creates, then appends
        result = sparks("entry", "add", "--json", json.dumps(record), cwd=tmp_path)
        assert result.returncode == 0, result.stderr
        assert result.stdout == f"added {record['id']} to sparks.json\n"
    assert json.loads((tmp_path / "sparks.json").read_bytes()) == [FIRST, SECOND]
    assert others(tmp_path) == []


def test_relative_path_resolves_against_the_working_directory(tmp_path):
    (tmp_path / "docs").mkdir()
    result = sparks(
        "entry", "add", "--path", "docs/notes.json", "--json", json.dumps(FIRST), cwd=tmp_path
    )
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / "docs" / "notes.json").read_bytes()) == [FIRST]


def test_appends_after_existing_records_and_keeps_them(tmp_path):
    path = tmp_path / "sparks.json"
    # Hand-written: compact, with keys in a different order.
    hand_written = {key: FIRST[key] for key in ("id", "answer", "question", "type")}
    path.write_bytes(json.dumps([hand_written]).encode())
    third = spark("Is a third record kept in order?", "Yes, at the end.")
    assert add(path, SECOND).returncode == 0
    assert add(path, third).returncode == 0
    records = json.loads(path.read_bytes())
    assert records == [FIRST, SECOND, third]
    assert list(records[0]) == ["id", "answer", "question", "type"]


def test_new_record_is_stored_in_schema_key_order(tmp_path):
    path = tmp_path / "sparks.json"
    shuffled = json.dumps({key: FIRST[key] for key in ("id", "answer", "question", "type")})
    assert add(path, shuffled).returncode == 0
    assert list(json.loads(path.read_bytes())[0]) == ["type", "question", "answer", "id"]


def test_non_ascii_is_kept_verbatim_and_hashed_by_the_spec_rule(tmp_path):
    question = "¿Por qué “verbatim”?"
    answer = "Naïve café prose — 日本語 🙂, kept as written."
    preimage = json.dumps(
        {"answer": answer, "question": question, "type": "SPARK"},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    record = {
        "type": "SPARK",
        "question": question,
        "answer": answer,
        "id": hashlib.sha256(preimage.encode("utf-8")).hexdigest()[-16:],
    }
    path = tmp_path / "sparks.json"
    result = add(path, record)
    assert result.returncode == 0, result.stderr
    text = path.read_bytes().decode("utf-8")
    assert question in text and answer in text  # no \u escapes
    assert json.loads(text) == [record]


def test_same_question_with_a_new_answer_is_appended_until_replace_exists(tmp_path):
    path = tmp_path / "sparks.json"
    revised = spark(FIRST["question"], "Every merge must pass CI and one review.")
    assert add(path, FIRST).returncode == 0
    assert add(path, revised).returncode == 0
    assert json.loads(path.read_bytes()) == [FIRST, revised]


def test_written_file_passes_spark_id_and_the_schema(tmp_path):
    path = tmp_path / "sparks.json"
    for record in (FIRST, SECOND):
        assert add(path, record).returncode == 0
    assert spark_id.main(["spark_id.py", str(path)]) == 0
    schema = json.loads((ROOT / "spark.schema.json").read_bytes())
    Draft202012Validator(schema).validate(json.loads(path.read_bytes()))


# rejections: --json

DROP = object()


def _payload(**changes):
    record = {**FIRST, **changes}
    return json.dumps({key: value for key, value in record.items() if value is not DROP})


BAD_INPUT = [
    pytest.param("{", "--json: invalid JSON: ", id="truncated"),
    pytest.param("", "--json: invalid JSON: ", id="empty"),
    pytest.param(json.dumps([FIRST]), "--json: expected one JSON object", id="array"),
    pytest.param('"text"', "--json: expected one JSON object", id="string"),
    pytest.param(
        _payload()[:-1] + ', "question": "again"}',
        "--json: duplicate key 'question'",
        id="duplicate-key",
    ),
    pytest.param(_payload(id=DROP), "--json: 'id' is a required property", id="missing-id"),
    pytest.param(
        _payload(answer=DROP), "--json: 'answer' is a required property", id="missing-answer"
    ),
    pytest.param(
        _payload(extra=1),
        "--json: Additional properties are not allowed ('extra' was unexpected)",
        id="extra-key",
    ),
    pytest.param(_payload(type="spark"), "--json: type: 'SPARK' was expected", id="wrong-type"),
    pytest.param(
        _payload(question=1), "--json: question: 1 is not of type 'string'", id="question-int"
    ),
    pytest.param(
        _payload(answer=None), "--json: answer: None is not of type 'string'", id="answer-null"
    ),
    pytest.param(
        _payload(id="ABCDEF0123456789"),
        "--json: id: 'ABCDEF0123456789' does not match '^[0-9a-f]{16}$'",
        id="id-uppercase",
    ),
    pytest.param(
        _payload(id="abc"), "--json: id: 'abc' does not match '^[0-9a-f]{16}$'", id="id-short"
    ),
    pytest.param(
        _payload(id="0" * 16),
        "--json: id 0000000000000000 does not match question and answer"
        f" (spark_id.py gives {FIRST['id']})",
        id="id-mismatch",
    ),
    pytest.param(_payload(question="\ud800"), "--json: preimage is not UTF-8", id="lone-surrogate"),
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
    payload = b'{"type": "SPARK", "question": "\xff", "answer": "a", "id": "0000000000000000"}'
    result = subprocess.run(
        [sys.executable, str(BIN), "entry", "add", "--path", str(path), "--json", payload],
        capture_output=True,
        encoding="utf-8",
    )
    assert_rejected(result, "sparks: --json: preimage is not UTF-8")
    assert not path.exists()


# rejections: the file

BAD_FILES = [
    pytest.param(b"", "invalid JSON: Expecting value", id="empty"),
    pytest.param(b"[", "invalid JSON: ", id="truncated"),
    pytest.param(b"\xef\xbb\xbf[]", "invalid JSON: Unexpected UTF-8 BOM", id="bom"),
    pytest.param(b"\xff[]", "file is not UTF-8", id="not-utf8"),
    pytest.param(b"{}", "{} is not of type 'array'", id="object"),
    pytest.param(b"[1]", "[0]: 1 is not of type 'object'", id="not-a-record"),
    pytest.param(
        json.dumps([{k: v for k, v in FIRST.items() if k != "id"}]).encode(),
        "[0]: 'id' is a required property",
        id="missing-id",
    ),
    pytest.param(
        json.dumps([{**FIRST, "id": "0" * 16}]).encode(),
        "stored id does not match the record",
        id="wrong-id",
    ),
    pytest.param(json.dumps([FIRST, FIRST]).encode(), "duplicate id", id="duplicate-record"),
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


def test_rejects_an_id_already_in_the_file(tmp_path):
    path = tmp_path / "sparks.json"
    before = seed(path, [FIRST, SECOND])
    assert_rejected(add(path, FIRST), f"sparks: {path}: id {FIRST['id']} is already in the file")
    assert path.read_bytes() == before
    assert others(tmp_path) == []


def test_rejects_a_directory_as_the_path(tmp_path):
    assert_rejected(add(tmp_path, FIRST, cwd=tmp_path), f"sparks: {tmp_path}: not a regular file")
    assert list(tmp_path.iterdir()) == []


def test_rejects_a_missing_parent_directory(tmp_path):
    path = tmp_path / "missing" / "sparks.json"
    assert_rejected(
        add(path, FIRST, cwd=tmp_path), f"sparks: {path}: parent directory does not exist"
    )
    assert list(tmp_path.iterdir()) == []


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


# atomic write


def test_failed_replace_keeps_the_old_file_and_no_temp_file(tmp_path, monkeypatch, capsys):
    path = tmp_path / "sparks.json"
    before = seed(path, [FIRST])

    def fail(src, dst):
        raise OSError(errno.EIO, "simulated I/O error")

    monkeypatch.setattr(os, "replace", fail)
    assert run_main(path, SECOND) == 1
    assert capsys.readouterr().err == f"sparks: {path}: simulated I/O error\n"
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
    assert capsys.readouterr().err == f"sparks: {path}: No space left on device\n"
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
def test_kill_before_replace_keeps_the_old_file(tmp_path):
    """SIGKILL skips all cleanup: the old file stays whole, and one hidden temp file is left."""
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
    (leftover,) = others(tmp_path)
    assert leftover.startswith(".sparks.json.") and leftover.endswith(".tmp")


def test_invalid_new_content_never_replaces_the_file(tmp_path, monkeypatch, capsys):
    path = tmp_path / "sparks.json"
    before = seed(path, [FIRST])
    monkeypatch.setattr(cli, "render", lambda records: '[{"type": "SPARK"}]\n')
    assert run_main(path, SECOND) == 1
    assert capsys.readouterr().err.startswith(f"sparks: {path} (new content): [0]: ")
    assert path.read_bytes() == before
    assert others(tmp_path) == []


@pytest.mark.parametrize(
    ("intruder", "message"),
    [
        ("[]\n", "changed by someone else during the write"),
        ("[", "re-validation after write failed"),
    ],
    ids=["valid-but-different", "invalid"],
)
def test_revalidation_reports_a_file_changed_after_replace(
    tmp_path, monkeypatch, capsys, intruder, message
):
    path = tmp_path / "sparks.json"
    seed(path, [FIRST])
    real_replace = os.replace

    def replace_then_clobber(src, dst):
        real_replace(src, dst)
        Path(dst).write_bytes(intruder.encode())

    monkeypatch.setattr(os, "replace", replace_then_clobber)
    assert run_main(path, SECOND) == 1
    assert message in capsys.readouterr().err


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
    argv = ["entry", "add", "--path", str(path), "--json", json.dumps(FIRST)]
    result = subprocess.run([sys.executable, str(BIN), *argv], capture_output=True, umask=0o027)
    assert result.returncode == 0, result.stderr
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


@posix
def test_writes_through_a_symlink(tmp_path):
    shared = tmp_path / "shared.json"
    seed(shared, [FIRST])
    link = tmp_path / "sparks.json"
    link.symlink_to("shared.json")
    assert add(link, SECOND).returncode == 0
    assert link.is_symlink()
    assert json.loads(shared.read_bytes()) == [FIRST, SECOND]


# help, TODO, and the uv entry point


def test_help_shows_the_usage_and_the_replace_todo(tmp_path):
    result = sparks("entry", "add", "--help", cwd=tmp_path)
    assert result.returncode == 0
    assert result.stdout.startswith("usage: sparks entry add [-h] [--path <path>] --json <json>\n")
    assert "TODO: replace is not supported yet" in result.stdout
    assert ISSUE_21 in result.stdout


def test_code_marks_replace_as_a_todo_for_issue_21():
    source = BIN.read_text(encoding="utf-8")
    assert "TODO(#21)" in source and ISSUE_21 in source


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
    assert result.stdout == f"added {FIRST['id']} to sparks.json\n"
    assert json.loads((tmp_path / "sparks.json").read_bytes()) == [FIRST]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-p", "no:cacheprovider", *sys.argv[1:]]))

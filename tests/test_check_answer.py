import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

P = Path(__file__).resolve().parents[1] / "skills" / "sparks-ingest" / "check_answer.py"
spec = importlib.util.spec_from_file_location("check_answer", P)
ca = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ca)


@pytest.fixture
def sources(tmp_path):
    (tmp_path / "a.ts").write_text(
        'const x = `@${file}`;\nlet  provider =\n  process.env.PI_PROVIDER;\n'
        'foo(); bar(); baz();\n"env", `PI_SUBAGENT_RUN_DIR=${metadata.runDir}`\n'
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "house.md").write_text("hi")
    return tmp_path


def check(sources, answer, typ="S", **extra):
    return ca.check({"type": typ, "question": "arbitrary unchecked prose", "answer": answer, **extra}, str(sources))


def cli(sources, spark, *args, stdin=False):
    command = [sys.executable, str(P), "--sources", str(sources), *args]
    data = json.dumps(spark)
    if not stdin:
        command += ["--json", data]
    return subprocess.run(command, input=data if stdin else None, text=True, capture_output=True)


def test_quote_whitespace_collapse(sources):
    ok, items = check(sources, "`let\nprovider = process.env.PI_PROVIDER;`")
    assert ok and items[0]["where"] == "a.ts"


def test_source_unicode_whitespace_and_bom(sources):
    (sources / "whitespace.txt").write_bytes("\ufeffalpha\v\f\u0085beta\u00a0gamma".encode("utf-8"))
    assert check(sources, "`alpha beta gamma`")[0]


def test_questions_never_checked(sources):
    assert check(sources, "`foo();`", question={"not": ["even a string"]})[0]


@pytest.mark.parametrize("answer,expected", [
    ("`foo(); … baz();`", True),
    ("`baz(); … foo();`", False),
    ("`foo(); ... baz();`", False),
    ("`foo(); … bar(); … baz();`", True),
    ("`… foo(); …`", True),
    ("`…`", False),
    ("`   `", False),
    ("`foo(); … hi`", False),  # Never combine pieces across files.
])
def test_ellipsis(sources, answer, expected):
    assert check(sources, answer)[0] is expected


@pytest.mark.parametrize("answer", [
    "`foo();`, `bar();`. [judge note]",
    "`foo();` — (`bar();`)!? / ‘`baz();`’",
    "`foo();`\v\u00a0`bar();`",
    "[A note with [nested brackets] and `non-source` text] `foo();`",
    "[only a note, accuracy is hand-judged]",
])
def test_notes_and_separators(sources, answer):
    assert check(sources, answer)[0]


@pytest.mark.parametrize("answer", [
    "From a.ts: `foo();`",
    "`foo();` (a.ts)",
    "`foo();` and `bar();`",
    "`foo();` + `bar();`",  # A symbol, not punctuation.
    "`nope();`",
    "`foo();",
    "`foo();` [unclosed note",
    "`foo();` ]",
    "`foo();` [nested [unclosed]",
    "",
    "... ;",
    None,
    42,
    ["foo();"],
])
def test_invalid_answers(sources, answer):
    assert not check(sources, answer)[0]


@pytest.mark.parametrize("answer", [
    "`const x = `@${file}`;` `foo();`",
    "``const x = `@${file}`;``",
    "`` `@${file}` ``",
    "`\"env\", `PI_SUBAGENT_RUN_DIR=${metadata.runDir}``",
    "``const x = `@${file}`;`` `foo();`",
    "```const x = `@${file}`;```",
])
def test_nested_backticks(sources, answer):
    ok, items = check(sources, answer)
    assert ok
    assert all(item["where"] == "a.ts" for item in items)


def test_double_backticks_use_nearest_equal_run(sources):
    # A long source match must not merge explicitly delimited Markdown spans.
    (sources / "ambiguous.md").write_text("first`` ``second")
    ok, items = check(sources, "``first`` ``second``")
    assert ok and [item["text"] for item in items] == ["first", "second"]
    assert ca.tokenize("``a ` b``` c``") == [("quote", "a ` b``` c")]


def test_single_backticks_do_not_close_on_next_opener(sources):
    (sources / "README.md").write_text('Expose the CLI on `PATH`:\n\n```sh\nrun\n```')
    ok, items = check(sources, "`PATH`: `foo();`")
    assert ok and [item["text"] for item in items] == ["PATH", "foo();"]


def test_missing_template_fails(sources):
    assert not check(sources, "``const x = `@${missing}`;``")[0]


@pytest.mark.parametrize("payload", [
    b"\0secret()",
    b"x" * 9000 + b"\0secret()",
    b"\xffsecret()",
    b"\x01secret()",
])
def test_binary_skipped(tmp_path, payload):
    (tmp_path / "b.dat").write_bytes(payload)
    assert not check(tmp_path, "`secret()`")[0]


def test_git_and_symlinks_skipped(tmp_path):
    refs = tmp_path / "refs"
    refs.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("external-secret")
    (refs / "link").symlink_to(outside)
    (refs / "directory-link").symlink_to(tmp_path, target_is_directory=True)
    (refs / ".git").mkdir()
    (refs / ".git" / "config").write_text("git-secret")
    (refs / "nested").mkdir()
    (refs / "nested" / ".git").write_text("worktree-secret")
    assert ca.load_sources(refs) == []


def test_fifo_skipped(tmp_path):
    import os
    os.mkfifo(tmp_path / "pipe")
    assert ca.load_sources(tmp_path) == []


def test_sources_are_only_search_root(tmp_path, monkeypatch):
    (tmp_path / "repo.txt").write_text("outside source directory")
    refs = tmp_path / "refs"
    refs.mkdir()
    monkeypatch.chdir(tmp_path)
    assert not check(refs, "`outside source directory`")[0]


@pytest.mark.parametrize("answer", [
    "https://example.com/x",
    "<https://example.com/x>",
    "[pi](https://github.com/earendil-works/pi)",
    "ftp://example.com/docs",
    "mailto:reader@example.com",
    "docs/house.md",
    "`docs/house.md`",
    "[docs](docs/house.md)",
    "docs",
    "./docs",
])
@pytest.mark.parametrize("typ", ["K", "k"])
def test_k_links(sources, answer, typ):
    ok, items = check(sources, answer, typ)
    assert ok and items[0]["kind"] == "link"
    if "exists" in items[0]:
        assert items[0]["exists"] is True


def test_k_missing_path_reports_existence_without_matching(sources):
    ok, items = check(sources, "docs/missing", "K")
    assert ok and items[0]["exists"] is False
    assert items[0]["where"] == str(sources / "docs/missing")


def test_k_unknown_home_directory(sources):
    ok, items = check(sources, "~sparks-checker-no-such-user/docs", "K")
    assert ok and items[0]["exists"] is False


def test_k_absolute_path(sources):
    ok, items = check(sources, str(sources / "a.ts"), "K")
    assert ok and items[0]["exists"] is True


def test_k_path_with_spaces(sources):
    (sources / "docs" / "house notes.md").write_text("hi")
    assert check(sources, "[notes](<docs/house notes.md>)", "K")[1][0]["exists"]


def test_k_other_answers_still_checked(sources):
    assert check(sources, "`foo();`", "K")[0]
    assert not check(sources, "unquoted prose", "K")[0]
    assert not check(sources, "From https://example.com/x", "K")[0]
    assert not check(sources, "https://example.com/x", "S")[0]
    assert not check(sources, "[pi](https://example.com) trailing text", "K")[0]


@pytest.mark.parametrize("stdin", [True, False])
def test_cli_success_and_output(sources, stdin):
    result = cli(sources, {"answer": "`foo();`"}, stdin=stdin)
    assert result.returncode == 0
    assert "PASS  quote" in result.stdout and "found in a.ts" in result.stdout
    assert "OVERALL PASS" in result.stdout


def test_cli_fail_and_json(sources):
    result = cli(sources, {"id": "spark-id", "answer": "`foo();` `nope` [note] prose"}, "--json-out")
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["pass"] is False and data["id"] == "spark-id"
    assert [item["ok"] for item in data["items"]] == [True, False, True, False]
    assert data["items"][0]["where"] == "a.ts"
    assert not result.stderr


def test_cli_local_path_existence(sources):
    result = cli(sources, {"type": "k", "answer": "docs/missing"})
    assert result.returncode == 0 and "exists: false" in result.stdout
    result = cli(sources, {"type": "k", "answer": "docs/house.md"}, "--json-out")
    assert json.loads(result.stdout)["items"][0]["exists"] is True


@pytest.mark.parametrize("data", ["bad json", "[]", "null", '"answer"'])
def test_cli_bad_input(sources, data):
    result = subprocess.run([sys.executable, str(P), "--sources", str(sources)],
                            input=data, text=True, capture_output=True)
    assert result.returncode == 2 and result.stderr
    assert "Traceback" not in result.stderr


def test_cli_missing_sources(tmp_path):
    assert cli(tmp_path / "missing", {"answer": "`foo();`"}).returncode == 2

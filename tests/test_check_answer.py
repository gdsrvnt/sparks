import importlib.util, json, pathlib, subprocess, sys

P = pathlib.Path(__file__).resolve().parents[1] / "skills" / "sparks-ingest" / "check_answer.py"
spec = importlib.util.spec_from_file_location("check_answer", P)
ca = importlib.util.module_from_spec(spec); spec.loader.exec_module(ca)


def src(tmp_path):
    (tmp_path / "a.ts").write_text("const x = `@${file}`;\nlet  provider =\n  process.env.PI_PROVIDER;\nfoo(); bar(); baz();\n")
    (tmp_path / "docs").mkdir(exist_ok=True); (tmp_path / "docs" / "house.md").write_text("hi")
    (tmp_path / "bin.dat").write_bytes(b"\0\0let provider")
    return tmp_path


def run(tmp_path, answer, typ="S"):
    return ca.check({"type": typ, "question": "anything at all", "answer": answer}, str(src(tmp_path)))[0]


def test_quote_whitespace_collapse(tmp_path):
    assert run(tmp_path, "`let provider = process.env.PI_PROVIDER;`")

def test_ellipsis_gap_and_order(tmp_path):
    assert run(tmp_path, "`foo(); … baz();`")
    assert not run(tmp_path, "`baz(); … foo();`")

def test_ascii_dots_literal(tmp_path):
    assert not run(tmp_path, "`foo(); ... baz();`")

def test_notes_and_separators(tmp_path):
    assert run(tmp_path, "`foo();`, `bar();`. [judge note]")

def test_prose_and_attribution_fail(tmp_path):
    assert not run(tmp_path, "From a.ts: `foo();`")
    assert not run(tmp_path, "`foo();` (a.ts)")

def test_missing_quote_fails(tmp_path):
    assert not run(tmp_path, "`nope();`")

def test_nested_backticks(tmp_path):
    assert run(tmp_path, "`const x = `@${file}`;` `foo();`")
    assert run(tmp_path, "``const x = `@${file}`;``")

def test_binary_skipped(tmp_path):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "b.dat").write_bytes(b"\0secret()")
    assert not ca.check({"answer": "`secret()`"}, str(tmp_path))[0]

def test_k_links(tmp_path):
    assert run(tmp_path, "https://example.com/x", "K")
    assert run(tmp_path, "[pi](https://github.com/earendil-works/pi)", "k")
    assert run(tmp_path, "docs/house.md", "K")
    assert not run(tmp_path, "docs/missing", "K")
    assert not run(tmp_path, "https://example.com/x", "S")

def test_cli_exit_codes(tmp_path):
    s = str(src(tmp_path))
    ok = subprocess.run([sys.executable, str(P), "--sources", s, "--json", json.dumps({"answer": "`foo();`"})])
    assert ok.returncode == 0
    bad = subprocess.run([sys.executable, str(P), "--sources", s], input=json.dumps({"answer": "prose"}), text=True, capture_output=True)
    assert bad.returncode == 1 and "FAIL" in bad.stdout

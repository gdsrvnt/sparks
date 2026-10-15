#!/usr/bin/env python3
"""Mechanical checker for proposed spark answers (stdlib only).

Usage:
  check_answer.py --sources <dir> --json '<spark json>' [--repo-root <dir>] [--json-out]
  echo '<spark json>' | check_answer.py --sources <dir>

Rules (see SKILL.md):
- The question is never checked.
- Type K: an answer that is a single link (URL, markdown link, or local path)
  passes without quote matching; local paths are checked for existence.
- Otherwise the answer may contain only backtick-quoted spans, [bracketed]
  notes, and separators (whitespace . , ; :). Anything else FAILs.
- Each quote must appear in one file under --sources after collapsing
  whitespace. A unicode ellipsis inside a quote is a gap (pieces in order,
  same file). ASCII "..." is literal.
- Backticks: a run of N backticks opens a span closed by the next run of
  exactly N backticks (Markdown). When several closers are possible (nested
  template literals inside single-backtick spans), the longest span whose
  text is found in the sources wins; if none is found, the nearest closer.
- A bare ellipsis between quotes counts as a separator.
Exit 0 if everything passes, 1 otherwise, 2 on usage errors.
"""
import argparse, json, os, re, sys

SEP = set(" \t\r\n.,;:\u2026")
WS = re.compile(r"\s+")
ELL = "\u2026"
URL = re.compile(r"^(https?://\S+|<https?://\S+>)$")
MDLINK = re.compile(r"^\[[^\]]*\]\(([^)\s]+)\)$")
PATH = re.compile(r"^`?([\w.\-~]+(?:/[\w.\-]+)+/?|[\w\-]+\.\w+)`?$")


def norm(s):
    return WS.sub(" ", s).strip()


def load_sources(root):
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x != ".git"]
        for f in files:
            p = os.path.join(d, f)
            if not os.path.isfile(p) or os.path.islink(p):
                continue
            try:
                b = open(p, "rb").read()
            except OSError:
                continue
            if b"\0" in b[:8192]:
                continue
            out.append((os.path.relpath(p, root), norm(b.decode("utf-8", "replace"))))
    return out


def find(quote, sources):
    pieces = [norm(x) for x in quote.split(ELL)]
    pieces = [x for x in pieces if x]
    if not pieces:
        return None
    for name, text in sources:
        pos = 0
        for pc in pieces:
            i = text.find(pc, pos)
            if i < 0:
                break
            pos = i + len(pc)
        else:
            return name
    return None


def tokenize(ans, is_found=lambda t: False):
    """Split an answer into (kind, text) items, kind in quote|note|text.

    A run of N backticks opens a span; candidate closers are later runs of
    exactly N backticks. The longest candidate whose body is found in the
    sources wins; if none is found, the nearest closer is used.
    """
    out, i, n = [], 0, len(ans)
    while i < n:
        c = ans[i]
        if c in SEP:
            i += 1
        elif c == "`":
            j = i
            while j < n and ans[j] == "`":
                j += 1
            k = j - i
            cands = [j + m.start() for m in re.finditer(r"`+", ans[j:]) if len(m.group()) == k]
            if not cands:
                out.append(("text", ans[i:].strip()))
                break

            def body(e):
                t = ans[j:e]
                if k > 1 and t.startswith(" ") and t.endswith(" ") and t.strip():
                    t = t[1:-1]
                return t

            end = next((e for e in reversed(cands) if is_found(body(e))), cands[0])
            out.append(("quote", body(end)))
            i = end + k
        elif c == "[" and "]" in ans[i:]:
            e = ans.index("]", i)
            out.append(("note", ans[i + 1:e]))
            i = e + 1
        else:
            e = i
            while e < n and ans[e] not in "`[":
                e += 1
            out.append(("text", ans[i:e].strip()))
            i = e
    return out


def check_link(ans, roots):
    a = ans.strip()
    m = MDLINK.match(a)
    target = m.group(1) if m else a
    if URL.match(target):
        return {"kind": "link", "text": target, "ok": True, "where": "url"}
    if PATH.match(target):
        p = target.strip("`")
        for r in roots:
            if r and os.path.exists(os.path.join(r, p)):
                return {"kind": "link", "text": p, "ok": True, "where": os.path.join(r, p)}
        return {"kind": "link", "text": p, "ok": False, "where": "path not found"}
    return None


def check(spark, sources_dir, repo_root=None):
    ans = spark.get("answer") or ""
    if str(spark.get("type", "")).upper() == "K":
        r = check_link(ans, [sources_dir, repo_root])
        if r:
            return r["ok"], [r]
    sources = load_sources(sources_dir)
    memo = {}
    def found(t):
        if t not in memo:
            memo[t] = find(t, sources)
        return memo[t]
    items = []
    for kind, text in tokenize(ans, lambda t: bool(found(t))):
        if kind == "quote":
            w = found(text)
            items.append({"kind": "quote", "text": text, "ok": bool(w), "where": w})
        elif kind == "note":
            items.append({"kind": "note", "text": text, "ok": True, "where": None})
        elif text:
            items.append({"kind": "text", "text": text, "ok": False, "where": None})
    if not items:
        items = [{"kind": "text", "text": "(empty answer)", "ok": False, "where": None}]
    return all(x["ok"] for x in items), items


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True)
    ap.add_argument("--json", dest="spark")
    ap.add_argument("--repo-root")
    ap.add_argument("--json-out", action="store_true")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.sources):
        print(f"sources dir not found: {a.sources}", file=sys.stderr)
        return 2
    try:
        spark = json.loads(a.spark if a.spark is not None else sys.stdin.read())
    except json.JSONDecodeError as e:
        print(f"bad spark json: {e}", file=sys.stderr)
        return 2
    ok, items = check(spark, a.sources, a.repo_root)
    if a.json_out:
        print(json.dumps({"slug": spark.get("title-slug"), "pass": ok, "items": items}, indent=2))
    else:
        for x in items:
            if x["kind"] == "note":
                print(f"NOTE  [{x['text']}] (hand-judge)")
                continue
            tag = "PASS" if x["ok"] else "FAIL"
            why = {"quote": f"found in {x['where']}" if x["ok"] else "not found in sources",
                   "text": "text outside quotes/brackets", "link": x["where"]}[x["kind"]]
            t = x["text"] if len(x["text"]) < 100 else x["text"][:97] + "..."
            print(f"{tag}  {x['kind']}: {t!r} -- {why}")
        print("OVERALL", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

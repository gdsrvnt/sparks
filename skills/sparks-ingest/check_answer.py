#!/usr/bin/env python3
"""Check answer provenance against one ingestion run's local reference directory.

Accept spark JSON via --json or stdin; --json-out emits machine-readable results.
Questions are ignored. See SKILL.md for syntax, backtick rules, and judge duties.
Exit codes: 0 = pass, 1 = fail, 2 = invalid invocation/input.
"""

import argparse
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import urlsplit

WS = re.compile(r"\s+")
ELL = "\u2026"
MDLINK = re.compile(r"^\[(?:[^\[\]\\]|\\.)*\]\(\s*(<[^<>\n]+>|[^\s()]+)\s*\)$")


def norm(text):
    return WS.sub(" ", text).strip()


def load_sources(root):
    """Read only regular, non-symlink text files; never traverse .git."""
    sources = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in sorted(files):
            path = Path(directory) / name
            if name == ".git" or path.is_symlink() or not path.is_file():
                continue
            try:
                # Strict decoding and control-byte rejection avoid accepting
                # binary fragments, including NULs past an initial read buffer.
                text = path.read_bytes().decode("utf-8-sig")
            except (OSError, UnicodeError):
                continue
            if any(unicodedata.category(c) == "Cc" and not c.isspace() for c in text):
                continue
            sources.append((os.path.relpath(path, root), norm(text)))
    return sources


def find(quote, sources):
    pieces = [norm(piece) for piece in quote.split(ELL) if norm(piece)]
    if not pieces:
        return None
    for name, text in sources:
        pos = 0
        for piece in pieces:
            start = text.find(piece, pos)
            if start < 0:
                break
            pos = start + len(piece)
        else:
            return name
    return None


def separator(char):
    # Delimiters are structural, not separators; unmatched ones must fail.
    return char.isspace() or (char not in "`[]" and unicodedata.category(char).startswith("P"))


def tokenize(answer, is_found=lambda text: False):
    """Yield quote/note/text items.

    Multi-backtick spans close at the next run of exactly the opening length,
    independently of source contents. Single-backtick spans retain legacy
    template-literal support: choose the longest source-matching candidate
    with balanced interior ticks (including adjacent closing ticks). If none
    matches, use the nearest tick so the failed quote is reported.
    """
    items = []
    i = 0
    while i < len(answer):
        if answer[i] == "`":
            start = i
            while i < len(answer) and answer[i] == "`":
                i += 1
            width = i - start
            if width == 1:
                # An outer closer follows zero or more paired interior ticks.
                # Never mistake the next span's opener for this span's closer.
                candidates = [m.start() for m in re.finditer("`", answer[i:])][::2]
            else:
                candidates = [m.start() for m in re.finditer(r"`+", answer[i:]) if len(m.group()) == width]
            candidates = [i + offset for offset in candidates]
            if not candidates:
                items.append(("text", answer[start:]))
                break

            def body(end):
                text = answer[i:end]
                # Markdown padding permits a literal backtick at either edge.
                if width > 1 and text.startswith(" ") and text.endswith(" ") and text.strip():
                    text = text[1:-1]
                return text

            end = candidates[0]
            if width == 1:
                end = next((end for end in reversed(candidates) if is_found(body(end))), end)
            items.append(("quote", body(end)))
            i = end + width
        elif answer[i] == "[":
            start = i
            depth = 1
            i += 1
            while i < len(answer) and depth:
                if answer[i] == "[":
                    depth += 1
                elif answer[i] == "]":
                    depth -= 1
                i += 1
            if depth:
                items.append(("text", answer[start:]))
            else:
                items.append(("note", answer[start + 1:i - 1]))
        else:
            start = i
            i += 1
            while i < len(answer) and answer[i] not in "`[":
                i += 1
            text = answer[start:i]
            if not all(separator(char) for char in text):
                items.append(("text", text.strip()))
    return items


def check_link(answer, sources_dir):
    target = answer.strip()
    match = MDLINK.fullmatch(target)
    if match:
        target = match.group(1)
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    try:
        url = urlsplit(target)
    except ValueError:
        return None
    if not any(c.isspace() for c in target) and url.scheme and (url.netloc or url.scheme == "mailto"):
        return {"kind": "link", "text": target, "ok": True, "where": "url"}
    # Backtick-wrapped local paths are common in existing sparks.json files.
    quoted = re.fullmatch(r"(`+)(.*?)\1", target)
    if quoted:
        target = quoted.group(2).strip()
    if not target or any(c in target for c in "\n\r\x00`[]"):
        return None
    if not (match or quoted) and any(c.isspace() for c in target):
        return None
    # An explicit path, filename, or existing bare directory is a local link;
    # arbitrary prose must still take the quote-checking path.
    try:
        path = Path(target).expanduser()
    except RuntimeError:  # Unknown ~user: still report a missing local target.
        path = Path(target)
    resolved = path if path.is_absolute() else Path(sources_dir) / path
    try:
        exists = resolved.exists()
    except OSError:
        exists = False
    if not ("/" in target or re.fullmatch(r"[^\s/]+\.[^\s/]+", target) or exists):
        return None
    return {"kind": "link", "text": target, "ok": True,
            "where": str(resolved), "exists": exists}


def check(spark, sources_dir):
    answer = spark.get("answer", "")
    if not isinstance(answer, str):
        return False, [{"kind": "text", "text": "(answer must be a string)", "ok": False, "where": None}]
    if str(spark.get("type", "")).upper() == "K":
        link = check_link(answer, sources_dir)
        if link:
            return True, [link]
    sources = load_sources(sources_dir)
    memo = {}

    def found(text):
        if text not in memo:
            memo[text] = find(text, sources)
        return memo[text]

    items = []
    for kind, text in tokenize(answer, lambda text: found(text) is not None):
        where = found(text) if kind == "quote" else None
        items.append({"kind": kind, "text": text,
                      "ok": kind == "note" or (kind == "quote" and where is not None), "where": where})
    if not items:
        items = [{"kind": "text", "text": "(empty answer)", "ok": False, "where": None}]
    return all(item["ok"] for item in items), items


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", required=True)
    parser.add_argument("--json", dest="spark", help="spark JSON (defaults to stdin)")
    parser.add_argument("--json-out", action="store_true")
    args = parser.parse_args(argv)
    if not os.path.isdir(args.sources):
        print(f"sources dir not found: {args.sources}", file=sys.stderr)
        return 2
    try:
        spark = json.loads(args.spark if args.spark is not None else sys.stdin.read())
    except json.JSONDecodeError as error:
        print(f"bad spark json: {error}", file=sys.stderr)
        return 2
    if not isinstance(spark, dict):
        print("spark JSON must be an object", file=sys.stderr)
        return 2
    ok, items = check(spark, args.sources)
    if args.json_out:
        print(json.dumps({"slug": spark.get("title-slug"), "id": spark.get("id"),
                          "pass": ok, "items": items}, ensure_ascii=False, indent=2))
    else:
        for item in items:
            if item["kind"] == "note":
                print(f"NOTE  [{item['text']}] (hand-judge)")
                continue
            tag = "PASS" if item["ok"] else "FAIL"
            if item["kind"] == "quote":
                why = f"found in {item['where']}" if item["ok"] else "not found in sources"
            elif item["kind"] == "link":
                why = item["where"]
                if "exists" in item:
                    why += f" (exists: {str(item['exists']).lower()})"
            else:
                why = "text outside quotes/brackets"
            text = item["text"]
            if len(text) > 100:
                text = text[:97] + "..."
            print(f"{tag}  {item['kind']}: {text!r} -- {why}")
        print("OVERALL", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

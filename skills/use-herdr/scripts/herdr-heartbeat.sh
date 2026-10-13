#!/usr/bin/env bash
# One process owns the baseline, deadlines, and report. No temporary files.
exec python3 - "$@" <<'PY'
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time


def positive(value):
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive number")
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return number


parser = argparse.ArgumentParser(prog="herdr-heartbeat.sh", description="Wake the bot when a herdr agent needs attention.")
selection = parser.add_mutually_exclusive_group()
selection.add_argument("--agents", help="comma-separated agent names or pane IDs")
selection.add_argument("--workspace", help="workspace ID, for example w7")
parser.add_argument("--expect", action="append", default=[], metavar="FILE")
parser.add_argument("--poll-seconds", type=positive, default=15)
parser.add_argument("--stall-minutes", type=positive, default=5)
parser.add_argument("--cap-minutes", type=positive, default=20)
args = parser.parse_args()
if not 10 <= args.poll_seconds <= 20:
    parser.error("--poll-seconds must be between 10 and 20")
if args.cap_minutes > 45:
    parser.error("--cap-minutes must not exceed 45")
if args.workspace and not re.fullmatch(r"w[0-9]+", args.workspace):
    parser.error("--workspace must be a workspace ID such as w7")
targets = [s.strip() for s in args.agents.split(",")] if args.agents is not None else None
if targets is not None and (not all(targets) or not targets):
    parser.error("--agents requires non-empty names or pane IDs")

started = time.monotonic()
deadline = started + args.cap_minutes * 60
stall_seconds = args.stall_minutes * 60
herdr = shutil.which("herdr") or "herdr"
watched = []
files = {}
ansi = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)")
spinner = re.compile(r"[\u2800-\u28ff◐◓◑◒⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]")
dialog = re.compile(
    r"(?:do you trust (?:the |this )?(?:files|folder|directory|workspace)|"
    r"trust (?:this |the )?(?:folder|directory|workspace)|"
    r"(?:trust|allow|enable).{0,50}hooks|"
    r"hooks need review|trust all and continue|"
    r"(?:would you like to|do you want to) (?:run|execute|allow|approve|proceed)|"
    r"(?:allow|approve) (?:this |the )?(?:command|tool|operation|action)|"
    r"(?:approval|permission) (?:required|requested)|"
    r"press enter to (?:confirm|continue)|"
    r"try the new fullscreen renderer\?|"
    r"^\s*(?:[!⚠✗×]\s*)?(?:api\s+)?(?:error|fatal)(?:\s*:|\s*\[)|"
    r"^\s*(?:authentication failed|connection failed|rate limit exceeded))",
    re.IGNORECASE | re.MULTILINE,
)
codes = {"blocked": 11, "missing": 15, "complete": 10, "file": 12,
         "stall": 13, "cap": 14, "error": 70, "none": 0}
BOTTOM_LINES = 12
BLOCK_POLLS = 2
live_activity = re.compile(r"esc to interrupt|^\s*›\s+(?!\d+\.)\S", re.IGNORECASE | re.MULTILINE)


def live_dialog(row_state, text):
    """Dialog only counts at the live bottom of the screen, never in scrollback,
    and never while the agent shows a working indicator or its input prompt."""
    lines = [l for l in text.splitlines() if l.strip()]
    bottom = "\n".join(lines[-BOTTOM_LINES:])
    if live_activity.search(bottom):
        return False
    return row_state == "blocked" or bool(dialog.search(bottom))


priority = ("blocked", "missing", "complete", "file", "stall", "cap")


class CapReached(Exception):
    pass


def cli(*command):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise CapReached()
    try:
        result = subprocess.run([herdr, *command], capture_output=True, text=True,
                                timeout=min(10, remaining), errors="replace")
    except subprocess.TimeoutExpired:
        if time.monotonic() >= deadline:
            raise CapReached()
        raise RuntimeError("herdr " + " ".join(command) + " timed out")
    if result.returncode:
        raise RuntimeError("herdr " + " ".join(command) + ": " +
                           (result.stderr or result.stdout).strip()[:500])
    return result.stdout


def listing(kind):
    command = [kind, "list"]
    if kind == "pane" and args.workspace:
        command += ["--workspace", args.workspace]
    payload = json.loads(cli(*command))
    if not isinstance(payload, dict) or not isinstance(payload.get("result"), dict):
        raise RuntimeError("unexpected herdr " + kind + " list response")
    rows = payload["result"].get(kind + "s")
    if not isinstance(rows, list) or any(not isinstance(r, dict) or
                                           not isinstance(r.get("pane_id"), str) for r in rows):
        raise RuntimeError("invalid herdr " + kind + " list rows")
    return rows


def snapshot():
    agents = {a["pane_id"]: a for a in listing("agent")}
    return {p["pane_id"]: {**agents.get(p["pane_id"], {}), **p} for p in listing("pane")}


def screen(pane):
    raw = cli("pane", "read", pane, "--source", "visible")
    # Herdr 0.9.3 prints text. Also accept servers that return a JSON envelope.
    if raw.lstrip().startswith("{"):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            pass
        else:
            body = payload.get("result", payload) if isinstance(payload, dict) else None
            if isinstance(body, dict):
                text = next((body[k] for k in ("text", "content", "output")
                             if isinstance(body.get(k), str)), None)
                if text is not None:
                    raw = text
    return ansi.sub("", raw).replace("\r", "")


def normalized(text):
    return "\n".join(spinner.sub("", line).rstrip() for line in text.splitlines()).strip()


def state(row, text):
    status = row.get("agent_status", "unknown")
    if status not in ("idle", "working", "blocked", "done", "unknown"):
        raise RuntimeError("invalid state for " + row["pane_id"] + ": " + str(status))
    if status == "unknown" and (row.get("agent") == "codex" or
                                  row.get("agent_session", {}).get("agent") == "codex"):
        if re.search(r"(?:Working|Thinking).{0,80}esc to interrupt", text, re.IGNORECASE):
            return "working"
        if re.search(r"^\s*›\s*(?:Ask Codex|Implement|Explain|Find|Summarize)", text, re.MULTILINE):
            return "idle"
    return status


def file_status(path):
    try:
        st = os.stat(path)
    except FileNotFoundError:
        return None
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def check_files():
    events = []
    for path, info in files.items():
        current = file_status(path)
        baseline = info["baseline"]
        info["current"] = current
        info["status"] = ("appeared" if baseline is None and current is not None else
                          "removed" if baseline is not None and current is None else
                          "changed" if baseline != current else
                          "missing" if current is None else "unchanged")
        if baseline != current:
            events.append(("file", path + " " + info["status"]))
    return events


def report(events):
    reason = next((r for r in priority if any(e[0] == r for e in events)), events[0][0])
    print(f"herdr heartbeat: {reason}; exit={codes[reason]}; elapsed={time.monotonic() - started:.1f}s")
    for _, detail in events:
        print("wake: " + detail)
    for item in watched:
        print(f"agent {item['name']} | pane={item['pane']} | state={item['state']}")
        lines = [line.rstrip() for line in item["text"].splitlines() if line.strip()]
        for line in lines[-6:]:
            print("  " + line[:240])
        if not lines:
            print("  (no visible output)")
    for path, info in files.items():
        size = f"; bytes={info['current'][2]}" if info["current"] is not None else ""
        print(f"expect {path}: {info['status']}{size}")
    return codes[reason]


def run():
    for path in dict.fromkeys(os.path.abspath(p) for p in args.expect):
        baseline = file_status(path)
        files[path] = {"baseline": baseline, "current": baseline,
                       "status": "missing" if baseline is None else "unchanged"}
    rows = snapshot()
    if targets is not None:
        selected = []
        for target in dict.fromkeys(targets):
            matches = [r for r in rows.values() if target in (r["pane_id"], r.get("name"))]
            if len(matches) != 1:
                raise RuntimeError("agent/pane target not found or ambiguous: " + target)
            if matches[0] not in selected:
                selected.append(matches[0])
    else:
        selected = [r for r in rows.values() if
                    (args.workspace and r.get("workspace_id") == args.workspace and
                     (r.get("agent") or r.get("agent_session") or r.get("name") or
                      r.get("agent_status") in ("working", "blocked"))) or
                    (not args.workspace and r.get("agent_status") == "working")]
    initial = []
    for row in selected:
        item = {"name": row.get("name") or row["pane_id"], "pane": row["pane_id"],
                "state": row.get("agent_status", "unknown"), "text": "",
                "last_change": time.monotonic(), "seen_working": False, "active": True}
        watched.append(item)
        item["text"] = screen(item["pane"])
        item["state"] = state(row, item["text"])
        item["seen_working"] = item["state"] == "working"
        item["active"] = item["state"] not in ("idle", "done")
        item["normalized"] = normalized(item["text"])
        # Never report blocked at startup: only count it toward persistence.
        item["block_streak"] = 1 if live_dialog(item["state"], item["text"]) else 0
    initial += check_files()
    if initial:
        return report(initial)
    if not any(item["active"] for item in watched):
        return report([("none", "nothing is running among the selected agents")])
    while True:
        now = time.monotonic()
        next_stall = min(item["last_change"] + stall_seconds for item in watched if item["active"])
        time.sleep(max(0, min(args.poll_seconds, deadline - now, next_stall - now)))
        if time.monotonic() >= deadline:
            # Use the last complete screen snapshot; never extend the cap for a final read.
            return report(check_files() +
                          [("cap", f"heartbeat cap of {args.cap_minutes:g} minutes reached")])
        rows = snapshot()
        events = []
        for item in watched:
            row = rows.get(item["pane"])
            if row is None:
                item["state"] = "unknown"
                events.append(("missing", item["name"] + " pane disappeared"))
                continue
            text = screen(item["pane"])
            current = state(row, text)
            new_screen = normalized(text)
            now = time.monotonic()
            if new_screen != item["normalized"]:
                item["last_change"] = now
            item.update(text=text, state=current, normalized=new_screen)
            item["block_streak"] = item.get("block_streak", 0) + 1 if live_dialog(current, text) else 0
            if item["block_streak"] >= BLOCK_POLLS:
                events.append(("blocked", item["name"] + " shows a dialog/error at the live prompt for "
                               + str(item["block_streak"]) + " consecutive reads"))
            if item["seen_working"] and current in ("idle", "done"):
                events.append(("complete", item["name"] + " changed from working to " + current))
            if current == "working":
                item["seen_working"] = True
                item["active"] = True
            if item["active"] and now - item["last_change"] >= stall_seconds:
                events.append(("stall", f"{item['name']} screen unchanged for {stall_seconds:g}s"))
        events += check_files()
        if time.monotonic() >= deadline:
            events.append(("cap", f"heartbeat cap of {args.cap_minutes:g} minutes reached"))
        if events:
            return report(events)


try:
    code = run()
except CapReached:
    code = report([("cap", f"heartbeat cap of {args.cap_minutes:g} minutes reached during a CLI read")])
except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
    code = report([("error", str(exc))])
sys.exit(code)
PY

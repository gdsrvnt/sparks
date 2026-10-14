---
name: subagent
description: Spawn a Pi subagent in tmux, observe its work, and wait for its durable assistant result in the JSONL session. Use for independent reviews or delegated repository work.
---

# Subagent

Spawn each subagent in a separate tmux session with a dedicated JSONL session file. Use `wait.ts` beside this file to wait for completion and read the result. Do not infer the result from terminal text.

## Spawn

1. Choose a short, unique tmux session name.
2. Create a temporary run directory with `mktemp -d`.
3. Write the complete task to `<run-dir>/prompt.md` with the `write` tool.
4. Create the exact session path before launch:

```sh
touch <run-dir>/session.jsonl
```

5. From the target working directory, start Pi in tmux. Use `./pi-test.sh` when it exists so a Pi source checkout runs its working-tree code. Otherwise use `pi`.

```sh
launcher=pi
test ! -x ./pi-test.sh || launcher=./pi-test.sh

tmux new-session -d -s <name> -x 120 -y 40 -c "$PWD" -- \
  "$launcher" \
  --session <run-dir>/session.jsonl \
  --provider "$PI_PROVIDER" \
  --model "$PI_MODEL" \
  --thinking "$PI_REASONING_LEVEL" \
  @<run-dir>/prompt.md
```

Pass arguments as separate shell words. Do not construct one quoted shell command. The current Pi model settings are available through `PI_PROVIDER`, `PI_MODEL`, and `PI_REASONING_LEVEL` in the bash tool environment.

Inspect progress when needed:

```sh
tmux capture-pane -t <name> -p
```

Do not kill the tmux session while the subagent is working.

## Wait and collect

Run the companion script against the exact session file:

```sh
node ~/.pi/agent/skills/subagent/wait.ts <run-dir>/session.jsonl
```

The script follows the active JSONL branch. It waits until the latest message is an assistant message with a terminal `stopReason`, then prints the latest assistant entry as JSON.

Options:

```text
--count <n>          Number of latest assistant entries to print (default: 1)
--timeout <seconds>  Maximum wait (default: 1800)
--poll <milliseconds> Poll interval (default: 500)
```

When invoking it through the bash tool, set the bash timeout longer than `--timeout`. A nonzero exit means the session could not be read or did not settle before the deadline.

## Cleanup

After collecting the result:

```sh
tmux kill-session -t <name>
rm -rf <run-dir>
```

Keep the run directory when the JSONL transcript is still needed for review.

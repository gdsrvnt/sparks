---
name: herdr-operations
description: Run coding-agent work in herdr, a terminal multiplexer for coding agents. Claude Code runs Anthropic models and pi runs xAI (Grok) and OpenAI models, one agent per tab, with proactive check-ins. Use when the user runs coding agents in herdr and a task should be handed to one.
---

# Herdr operations

herdr is a terminal multiplexer for coding agents. It organizes **workspaces** (`w1`), **tabs** (`w1:t1`) and **panes** (`w1:p1`), recognizes the coding agent running in each pane, and reports its state: `idle`, `working`, `blocked`, `done` or `unknown`. You drive it with the `herdr` CLI, and most commands return JSON. Read IDs from those responses; never guess them.

## Where work runs

- Run agent and coding work in herdr on the machine the user has set aside for it, not on the user's personal computer unless they ask. Don't move work to a hosted cloud agent unless the user asks for one in that request.
- Choose the harness from the model's maker:
  - Anthropic models run in **Claude Code** (`--kind claude`): `claude --model <model>`, with `--effort <level>` for effort.
  - xAI (Grok) and OpenAI models run in **pi** (`--kind pi`): `--provider xai --model <grok-model>` or `--provider openai-codex --model <openai-model>`. Pass them after `--`, e.g. `herdr agent start <name> --kind pi --pane <id> -- --provider xai --model <grok-model>`. Append `:<thinking>` to the model for effort (e.g. `<model>:high`). List models with `pi --list-models`.
  - **Only pi and the Claude Code CLI are ever used in herdr; never any other harness.** xAI and OpenAI models always run in pi. Don't install others.
  - Check that each harness is logged in before launching: `claude auth status` for Claude Code; pi's provider logins for pi. Install herdr's pi integration so herdr reports pi's state.
  - pi loads skills from its user skills folder and from the repo's `.agents/skills`. Add a symlink there when you add a shared skill. Skills marked `disable-model-invocation` are only run by name: `/skill:<name>`.
- Within one process, each step can use a different harness. Run each step in the harness that matches its model.

## Core loop

1. **Look first.** Run `herdr status server`, `herdr workspace list` and `herdr pane list`, and tell the user what's already running before you change anything. Don't run bare `herdr`: it opens the interactive screen. Then refresh the shared herdr state database (see Shared herdr state) before you change anything.
2. **One workspace per repository**, rooted at that repo's own clone. Clone it, or `git fetch` and fast-forward a clean default branch. Never do repo X's work in repo Y's clone.
3. **Give each agent its own tab and a name that says its job.** One agent per tab, never split a tab for a second agent. Create a new tab (`herdr tab create`), then `herdr agent start <name> --kind <claude|pi> --pane <pane id>`. Name it for the task from the start, short, like `docs-audit` or `test-count`, never by harness like `docs-grok`. Names match `[a-z][a-z0-9_-]{0,31}`.
4. **Prompt, then confirm it took.** Use `herdr agent prompt <name> "<task>"` (add `--wait` only for short tasks). Then read the pane with `--source visible` and confirm the agent is actually working. An unregistered agent can be prompted with `herdr pane run <pane> "<task>"`. Don't put slash commands for skills that aren't installed in the prompt: Claude Code rejects unknown ones and runs nothing.
5. **Check in proactively.** Don't wait to be asked. Run `scripts/herdr-heartbeat.sh` (relative to this skill's folder) in the background after launching agents, and read each agent when it wakes you. Refresh that database immediately before you start the heartbeat, and again when it wakes you, before you act on the report.
6. **Read the result.** Use `herdr agent read <name> --source recent-unwrapped` once it's idle, or `--source visible` while it's working. A settled prompt doesn't prove the work happened. Have the agent write its result to a file, then check that file and the real diff or output before you report.
7. **Clean up only what you created.** Close your own panes and tabs. Never close the user's.

## Shared herdr state

Agents that share a machine share one local SQLite database of herdr state: every workspace, tab, pane, and agent, and the status of each agent. `sparks herdr snapshot` (the `bin/sparks` script in this repository) refreshes it. The command runs `herdr workspace list`, `herdr tab list`, `herdr pane list`, and `herdr agent list`. It never runs bare `herdr`.

The database path is `--db`, or `SPARKS_HERDR_DB`, or otherwise `$XDG_DATA_HOME/sparks/herdr-state.sqlite` (`~/.local/share/sparks/herdr-state.sqlite` when `XDG_DATA_HOME` is unset). On a shared machine, leave the path at that default, or set `SPARKS_HERDR_DB` to the one path the user named. Do not invent a second file. Do not commit the database.

Read it with `sparks herdr query`. That command does not call herdr and does not write the database. If it reports pending journal data, retry after the snapshot writer closes; do not checkpoint the database yourself. The default view prints the snapshot time, stored counts, status counts, and agents whose status is not exactly `done`. `sparks herdr query agents` lists every agent. Columns are the parsed list fields, tab-separated. Pass `--raw` only when the stored fetch object is required. Same path rules as snapshot.

Refresh it:

- when you look first, before you create, close, split, start, rename, or prompt
- after each of those herdr changes
- immediately before you start `scripts/herdr-heartbeat.sh`, and again when it wakes you, before you act on the report

A snapshot from this turn is fresh enough to tell the user what is running. `sparks herdr query` prints that snapshot; it is not a live herdr response. It is not fresh enough, later, to choose an id for a mutation. Read ids from a herdr JSON response in the turn you use them. Never guess an id from an older database row. Repeat herdr's `agent_status` as given. Workspace and tab statuses are herdr's fields, not a rollup you recompute.

If the snapshot exits nonzero, say the one-line error and do not claim the database was updated. If herdr is missing or not running, follow "If herdr isn't running" below. A failed snapshot does not by itself send the work to another machine.

## Hard rules

- Never answer another agent's approval or question dialog (`blocked`). Show it to its owner.
- A `pane run` exit code of 0 only means the text was sent. Verify the effect.
- Don't blindly resend a prompt. Read the screen first.
- Never pass `--group`, and don't stop the herdr server or session.
- **Use the configured bot identity for GitHub.** If the user has set up a bot account for agent work, every agent's `gh` and `git` work uses it: point `GH_TOKEN` at that account's token and author commits as that account. Put that in every launch prompt that touches GitHub. Use the user's personal account only with their explicit permission, when a task can't be done as the bot.

## If herdr isn't running

Start the herdr server the way your setup does. If that fails, or herdr isn't installed, report the exact error in one sentence and ask the user how to proceed. Don't switch to another machine or to cloud agents on your own.

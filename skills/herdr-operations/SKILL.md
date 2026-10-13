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
  - Use only the harnesses the user has approved. Don't install others.
  - Check that each harness is logged in before launching: `claude auth status` for Claude Code; pi's provider logins for pi. Install herdr's pi integration so herdr reports pi's state.
  - pi loads skills from its user skills folder and from the repo's `.agents/skills`. Add a symlink there when you add a shared skill. Skills marked `disable-model-invocation` are only run by name: `/skill:<name>`.
- Within one process, each step can use a different harness. Run each step in the harness that matches its model.

## Core loop

1. **Look first.** Run `herdr status server`, `herdr workspace list` and `herdr pane list`, and tell the user what's already running before you change anything. Don't run bare `herdr`: it opens the interactive screen.
2. **One workspace per repository**, rooted at that repo's own clone. Clone it, or `git fetch` and fast-forward a clean default branch. Never do repo X's work in repo Y's clone.
3. **Give each agent its own tab and a name that says its job.** One agent per tab, never split a tab for a second agent. Create a new tab (`herdr tab create`), then `herdr agent start <name> --kind <claude|pi> --pane <pane id>`. Name it for the task from the start, short, like `docs-audit` or `test-count`, never by harness like `docs-grok`. Names match `[a-z][a-z0-9_-]{0,31}`.
4. **Prompt, then confirm it took.** Use `herdr agent prompt <name> "<task>"` (add `--wait` only for short tasks). Then read the pane with `--source visible` and confirm the agent is actually working. An unregistered agent can be prompted with `herdr pane run <pane> "<task>"`. Don't put slash commands for skills that aren't installed in the prompt: Claude Code rejects unknown ones and runs nothing.
5. **Check in proactively.** Don't wait to be asked. Run `scripts/herdr-heartbeat.sh` (relative to this skill's folder) in the background after launching agents, and read each agent when it wakes you.
6. **Read the result.** Use `herdr agent read <name> --source recent-unwrapped` once it's idle, or `--source visible` while it's working. A settled prompt doesn't prove the work happened. Have the agent write its result to a file, then check that file and the real diff or output before you report.
7. **Clean up only what you created.** Close your own panes and tabs. Never close the user's.

## Hard rules

- Never answer another agent's approval or question dialog (`blocked`). Show it to its owner.
- A `pane run` exit code of 0 only means the text was sent. Verify the effect.
- Don't blindly resend a prompt. Read the screen first.
- Never pass `--group`, and don't stop the herdr server or session.
- **Use the configured bot identity for GitHub.** If the user has set up a bot account for agent work, every agent's `gh` and `git` work uses it: point `GH_TOKEN` at that account's token and author commits as that account. Put that in every launch prompt that touches GitHub. Use the user's personal account only with their explicit permission, when a task can't be done as the bot.

## If herdr isn't running

Start the herdr server the way your setup does. If that fails, or herdr isn't installed, report the exact error in one sentence and ask the user how to proceed. Don't switch to another machine or to cloud agents on your own.

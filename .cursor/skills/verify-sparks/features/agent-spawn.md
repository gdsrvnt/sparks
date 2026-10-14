# Agent spawn

Agent spawn launches one persona from the nearest `.sparks/agents.toml` as a pi session in a new herdr tab. The user runs `sparks agent spawn <type>`. Verification only drives `--dry-run`, which calls `pi --list-models` and no herdr command, so it never opens a tab or starts an agent.

## Sub-features

- `spawn-plan` turns a persona into `pi --provider <p> --model <m> --thinking <level>`, reading the config from a parent directory.
- `spawn-unknown` refuses a type that is not a persona and lists the personas.
- `spawn-smuggle` refuses a persona flag inside `--additional-flags`.
- `spawn-unreachable` reports a missing pi instead of calling the run a pass.

## How to get to it (user POV)

- Run `bin/sparks agent spawn <type>` in a project, or any directory under it, that has `.sparks/agents.toml`.
- Add `--dry-run` to print the plan as one JSON line instead of launching.
- Add `--additional-flags "<string>"` to append pi flags, and `--timeout <seconds>` to change herdr's start timeout.
- Run `/agent-personas` to create or edit `.sparks/agents.toml` from `defaults/agent.toml`.

## Driving it with check-verify-sparks

Preconditions:

- `check-verify-sparks doctor` ended with `doctor: OK`.
- `pi` is on `PATH` and `pi --list-models` lists at least one model.

- **Plan.** Run `check-verify-sparks agent-spawn`. The helper takes the first row of `pi --list-models`, writes a `probe` persona with that provider and model and effort `none` to `<scratch>/.sparks/agents.toml`, and runs `uv run --script bin/sparks agent spawn probe --dry-run` from `<scratch>/sub`. It passes only if the plan's `command` is exactly `pi --provider <p> --model <m> --thinking off` and its `config` is the scratch file.
- **Unknown type.** The same command runs `agent spawn nope --dry-run`. It must exit `1` with one `sparks: ` line naming `personas: probe`.
- **Smuggle.** The same command runs `agent spawn probe --dry-run --additional-flags "--model x"`. It must exit `1` with one `sparks: ` line saying `--model is set by the persona`.
- **Unreachable.** If `pi` is missing or lists no model, the command exits `3`, writes `agent-spawn.txt`, and prints `UNREACHABLE` plus the prerequisite. That is not a pass and not a product failure.
- **Not exercised.** A real launch (`herdr tab create`, `herdr agent start`) is not driven: it opens a tab in the user's herdr. Do not drop `--dry-run` to "confirm" it.
- **Proof.** Quote the plan line or the `UNREACHABLE` line, and the three drives in `agent-spawn.txt`. The scratch directory is gone after the command returns.

## Gotchas

- The dry run still calls `pi --list-models`. A provider that pi lists but is not logged in passes here and fails at launch.
- The persona comes from pi's first listed model, so the plan differs between machines. The proof is that the command matches that row, not a fixed model.
- A `.sparks/agents.toml` above the scratch directory cannot win: the scratch one is nearer.

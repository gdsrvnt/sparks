# Agent spawn

Agent spawn launches one persona, from the nearest `.sparks/agents.toml` or the plugin's `defaults/agents.toml`, as a pi session in a new herdr tab. It walks the persona's model-type chain when a combo is unavailable, fails to start, or (with `--prompt`) ends in an API error. The user runs `sparks agent spawn <type>`. Verification only drives `--dry-run`, which calls `pi --list-models` and no herdr command, so it never opens a tab or starts an agent.

## Sub-features

- `spawn-plan` turns a persona into `pi --provider <p> --model <m> --thinking <level> -e <plugin>/pi/extensions/sparks-api-error-blocked.ts --append-system-prompt <sparks prompt>`, reading the config from a parent directory.
- `spawn-unknown` refuses a type that is not a persona and lists the personas.
- `spawn-smuggle` refuses a persona flag (`--model`, `--tools`) inside `--additional-flags`.
- `spawn-default` plans the shipped `reviewer` from `defaults/agents.toml`: `--exclude-tools edit,write`, `--no-skills`, and only the `spark-verification` skill.
- `spawn-unreachable` reports a missing pi instead of calling the run a pass.

## How to get to it (user POV)

- Run `bin/sparks agent spawn <type>` in a project, or any directory under it. The type is a persona in `.sparks/agents.toml` or one of the shipped `spec-writer`, `implementer`, `reviewer`.
- Add `--dry-run` to print the plan as one JSON line instead of launching. The plan shows the model-type `chain` and the `chosen` combo.
- Add `--prompt "<text>"` (and `--watch <seconds>`) to send a first prompt and fall back on an API error.
- Add `--additional-flags "<string>"` to append pi flags, and `--timeout <seconds>` to change herdr's start timeout.
- Run `/agent-personas` to create or edit `.sparks/agents.toml` from `defaults/agent.toml`, or `.sparks/model-types.toml`.

## Driving it with check-verify-sparks

Preconditions:

- `check-verify-sparks doctor` ended with `doctor: OK`.
- `pi` is on `PATH` and `pi --list-models` lists at least one model.

- **Plan.** Run `check-verify-sparks agent-spawn`. The helper takes the first row of `pi --list-models` and writes a `probe` persona with model type `fast`, that provider and model, and effort `none`, to `<scratch>/.sparks/agents.toml`. It then runs `uv run --script bin/sparks agent spawn probe --dry-run` from `<scratch>/sub`. It passes only if the plan's `command` starts `pi --provider <p> --model <m> --thinking off -e <repo>/pi/extensions/sparks-api-error-blocked.ts --append-system-prompt`, the next word is the sparks prompt, and its `config` is the scratch file.
- **Unknown type.** The same command runs `agent spawn nope --dry-run`. It must exit `1` with one `sparks: ` line naming `personas: probe`.
- **Smuggle.** The same command runs `agent spawn probe --dry-run --additional-flags "--model x"`, then `"--tools read"`. Each must exit `1` with one `sparks: ` line saying `--model is set by the persona` or `--tools is set by the persona`.
- **Shipped reviewer.** The same command runs `agent spawn reviewer --dry-run`, which falls back to `defaults/agents.toml`. If pi lists a `powerful`, `value`, or `fast` combo, the plan must read `defaults/agents.toml` and carry `--exclude-tools edit,write`, `--no-skills`, and the repo's `skills/spark-verification`. If pi lists none of them, the refusal must say `no combo for model type powerful is available`.
- **Unreachable.** If `pi` is missing or lists no model, the command exits `3`, writes `agent-spawn.txt`, and prints `UNREACHABLE` plus the prerequisite. That is not a pass and not a product failure.
- **Not exercised.** A real launch (`herdr tab create`, `herdr agent start`, `herdr agent prompt`, `herdr tab close`) and the api-error extension inside pi are not driven: they open tabs in the user's herdr and spend tokens. Do not drop `--dry-run` to "confirm" it. `tests/test_sparks.py` covers the fallback with a fake herdr, and the extension with node.
- **Proof.** Quote the plan line or the `UNREACHABLE` line, and the drives in `agent-spawn.txt`. The scratch directory is gone after the command returns.

## Gotchas

- The dry run still calls `pi --list-models`. A provider that pi lists but is not logged in, or whose key is wrong, passes here; at launch, with `--prompt`, its API error makes spawn fall back.
- The persona comes from pi's first listed model, so the plan differs between machines. The proof is that the command matches that row, not a fixed model.
- A `.sparks/agents.toml` above the scratch directory cannot win: the scratch one is nearer.
- `allowed_directories` only shows up as text in an `--append-system-prompt`; pi does not enforce it, so there is nothing more to verify.

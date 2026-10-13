# Herdr heartbeat

Run this command through the bot's background-shell facility after starting
agents. Its exit wakes the bot. Keep stdout attached, inspect the report, and
relaunch after handling the agents.

```bash
skills/use-herdr/scripts/herdr-heartbeat.sh --cap-minutes 20 --stall-minutes 5 --poll-seconds 15
```

The default watches every agent currently reported as working. `--workspace wN`
watches detected agents in that workspace, including agents absent from the
registry. `--agents build,review,wN:p1` selects names or exact pane IDs, including
unknown raw panes. These selectors are mutually exclusive. Replace example IDs
with IDs returned by herdr. The selected panes stay fixed for each run.

`--expect FILE` is repeatable. Relative paths use the launch directory. Creation,
replacement, metadata changes, and deletion wake the bot. Existing files get a
stat baseline and do not wake it immediately. The watcher does not read contents.

Defaults are `--poll-seconds 15 --stall-minutes 5 --cap-minutes 20`. Polling must
be between 10 and 20 seconds. Both minute options accept positive fractions for
short tests. The cap cannot exceed 45 minutes. CLI calls have a 10-second timeout
and cannot extend the cap. A deadline can shorten the normal polling sleep.

| Exit | Reason |
| --- | --- |
| 0 | No selected agents are running |
| 10 | A watched agent went from working to idle or done |
| 11 | An agent is blocked or shows a trust, approval, or error prompt |
| 12 | An expected file appeared, changed, or disappeared |
| 13 | A watched screen stayed unchanged for the stall interval |
| 14 | The heartbeat cap expired |
| 15 | A watched pane disappeared |
| 70 | A CLI, JSON, filesystem, or target-selection error |
| 2 | Invalid options |

Reports include every agent's name, pane, state, six non-empty screen lines, and
each expected file's status. Simultaneous events all appear. Exit-code priority
is blocked, missing pane, completion, file, stall, cap. Cap and CLI error reports
use the last available screen snapshot.

Dependencies are Bash, Python 3, and herdr. The Bash entry point becomes one
Python process. It uses `herdr` on PATH. It only lists
agents and panes and reads visible screens.

A stall means no visible change after removing terminal escapes and spinner
glyphs. Changing timers can prevent stalls; the cap still applies. Dialog
detection can match quoted prompt text. A whole turn completed between polls or
before startup can escape state detection; expected files and the cap still apply.

Blocked (exit 11) requires a dialog in the last 12 non-empty lines of the screen for 2 consecutive polls (BLOCK_POLLS=2). It is never reported at startup, and working screens (esc to interrupt, live input prompt) are skipped.

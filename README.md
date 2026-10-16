# sparks

> Spark is a way of engineering the context of a project or a repository in such a fashion that makes the information have three things that current approaches to context management don't have.

## Purpose

the purpose of the sparks is simple and explicit: They are ammunition for spark-verification, which checks a PR or branch's changed files against the sparks.json answers that apply to those files' directories. the thesis of spark is that if verification against human intent is the highest leverage asset in the age of orchestration, then the default best move on the board is to invest in the pipelines that distill that intent in almost-real time as agents run.

## Cursor plugin

This repository is a single Cursor plugin. The manifest is `.cursor-plugin/plugin.json` (`name`: `sparks`, package version `0.1.0`).

sparks gathers, maintains, and structures project context as question-and-answer pairs. It is built for coding agents and usable in any harness.

### Installation

After the plugin is listed, install it from Customize: find sparks and choose Install.

To load this repository locally before it is published:

1. Copy this plugin into `~/.cursor/plugins/local/sparks`, including `.cursor-plugin/plugin.json`, the component directories, `docs/` (the `why` skill reads `docs/uncovering-intention.md`), `defaults/` (the `agent-personas` skill copies `defaults/agent.toml`, and `sparks agent spawn` reads `defaults/agents.toml` and `defaults/model-types.toml`), and `pi/` (`sparks agent spawn` loads `pi/extensions/sparks-api-error-blocked.ts` into every pi it launches).
2. Reload Cursor.
3. Open Customize and confirm the plugin is present.

Cursor loads local plugins from that folder when local plugin imports are allowed. Submit the public repository at [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish) when it is ready for review.

### Components

Discovery uses the default folders. The manifest does not set custom component paths.

| Component | Path | Status |
| --- | --- | --- |
| Skills | `skills/` | `sparks-discuss`, `sparks-domain`, `sparks-postcall`, `spark-voice`, `spark-verification`, `study`, `herdr-operations`, and `agent-personas`; `ketchup`, `how`, `why`, `bro`, `create-verification-skill`, and `maintain-verification-skill` from poteto's pstack; and `show-me` from HumanLayer. See `THIRD_PARTY_NOTICES.md`. |
| Rules | `rules/` | `blocker-clearing`: when work is blocked on you, the agent asks one multiple-choice question with options that each clear the blocker, a free-text field, and a stop-and-deliberate option that runs `sparks-discuss` and records the outcome as a spark. `post-call-self-healing`: after every voice call ends, the agent runs the `sparks-postcall` self-healing procedure in full (opens `skills/sparks-postcall/SKILL.md`, or asks you to run `/sparks-postcall`). The post-call protocol lives only in `sparks-postcall`, not in `spark-voice`. |
| Agents | `agents/` | Not included. |
| Commands | `commands/` | Not included. |
| Hooks | `hooks/hooks.json` | Not included. |
| MCP servers | `mcp.json` | Not included. |
| pi extension | `pi/extensions/` | `sparks-api-error-blocked.ts`: reports a pi API error to herdr as blocked, so `sparks agent spawn` can fall back. pi loads it, not Cursor; see [API errors](#api-errors-the-bundled-pi-extension). |
| Defaults | `defaults/` | `agent.toml` (golden persona schema), `agents.toml` (shipped personas), `model-types.toml` (shipped model types). |

Cursor discovers plugin skills from `skills/` and rules from `rules/`.

`sparks-discuss` interviews you, one persona at a time, and writes your answers verbatim into `sparks.json` with `sparks add`. `spark-verification` is read-only: for a PR or branch it lists the diff, loads every `sparks.json` that applies to each changed file's directory (ancestors apply globally by default; see below), and reports violations with the file and the quoted spark. It never edits code or opens PRs. poteto's `create-verification-skill` and `maintain-verification-skill` remain bundled for direct use; `spark-verification` no longer wraps them.

## How to use spark

In a given directory, the sparks.json holds question answer pairs that pertain to stack questions in that particular directory.

### `sparks add`

`bin/sparks` adds one spark at a time to a `sparks.json` list. It is a [uv](https://docs.astral.sh/uv/) script, so uv installs its one dependency, `jsonschema`, on first run. It works in the current directory, so run it from the project that keeps the `sparks.json`:

```sh
cd path/to/project
path/to/sparks/bin/sparks add --json '{"type":"s","question":"What is spark?","answer":"spark is a way of gathering, maintaining, and structuring context about a project in Q&A pairs."}'
# added <id> to sparks.json
```

- `--path <path>` names the file. Without it, the command uses `sparks.json` in the current directory. A missing file is created; a missing directory is not.
- `--json <json>` is one spark. It must match `sparks.schema.json`: `type` is `s`, `p`, `a`, `r`, or `k` (any case is accepted; it is written lowercase), plus `question` and `answer`. Leave out `id`: sparks assigns it on insertion as XXH64 of the spark (computed by the bundled, dependency-free `spark_hash.py`), writes it to the file as the spark's `id`, and prints it on the success line. `id` is optional in the schema, so files without ids stay valid.
- The command matches `question` exactly within the target file. One match replaces the whole spark (including `type` and `answer`) in place; no match appends. Matching compares decoded JSON strings, with no trimming, case folding, punctuation removal, or Unicode normalization. Different JSON escape spellings of the same string match. An identical spark that already has its stored id succeeds without rewriting (an identical spark without one is rewritten once to add its id); the success line remains `added <id> to <path>` for both adds and replacements. A replacement keeps the id the spark already stored, so references to it survive; a spark without one gets one.
- Multiple exact-question matches are ambiguous: the command refuses without writing, even if one spark is identical to the incoming spark. Resolve them manually first; the CLI never chooses the first match or silently deletes duplicates.
- The command refuses invalid JSON, a schema failure, and an existing file that is not valid. It also refuses duplicate keys in a JSON object, which `spark_id.py` lets through, because rewriting the file would keep only one of them. A refusal exits 1 with one line on stderr and leaves the file alone.
- Each add rewrites the whole file with two-space indents and unescaped UTF-8, so a hand-formatted file is reformatted on its first add. The new file goes to a temp file in the same directory, `os.replace` moves it into place, and the file is read back and checked. Exit status 3 means it was written but read back different. Symlinks are followed and the mode is kept, but hard links, the owner, ACLs, and extended attributes do not carry over to the new file.
- On POSIX systems such as Linux and macOS, adds in one directory take turns by locking a short-lived `.sparks.lock` file there. Windows has no lock, so run one add per file at a time.
- Fuzzy duplicate flagging is not implemented. See the [design suggestions](docs/duplicate-detection.md) for its proposed evolution; only exact questions trigger replacement ([#21](https://github.com/gdsrvnt/sparks/issues/21)).

`bin/spark`, without the s, is an unrelated placeholder that does nothing. On Windows, run `uv run --script bin/sparks add ...`.

Verify this repository with [`.cursor/skills/verify-sparks/SKILL.md`](.cursor/skills/verify-sparks/SKILL.md), not with the pytest files. Source-wide semantic contradiction is the check that matters. The helper `check-verify-sparks` may also run the published XXH64 vectors and one `sparks add` path. `tests/test_sparks.py` and `tests/test_spark_hash.py` are the mechanical kernel for CLI and snapshot failures a prose read cannot see. They are not the spec. Do not add phrase locks there.

### `sparks herdr snapshot`

`bin/sparks herdr snapshot [--db <path>]` non-interactively calls `herdr workspace list`, `herdr tab list`, `herdr pane list`, and `herdr agent list` to refresh a shared local SQLite database. It never runs bare `herdr`.

The path is `--db`, else `SPARKS_HERDR_DB`, else `$XDG_DATA_HOME/sparks/herdr-state.sqlite` when `XDG_DATA_HOME` is set and non-empty, otherwise `~/.local/share/sparks/herdr-state.sqlite`.

Success prints one stdout line with the UTC snapshot time and row counts:

```text
snapshot <captured_at> workspaces=<n> tabs=<n> panes=<n> agents=<n> db=<path>
```

The database is current state, not a history log. A failed run leaves the previous file unchanged. Exit 1 reports a snapshot failure (including herdr missing or not running) with one stderr line; exit 2 reports a usage error.

herdr can list an agent with no name. `name` is the `agents` primary key, so that agent is not stored in `agents` and does not count toward `agents=<n>`. Its pane is still stored in `panes`, with the pane's `agent` and `agent_status`. The snapshot still succeeds and prints one `sparks: warning:` stderr line for each such agent, naming its pane.

### `sparks herdr query`

`bin/sparks herdr query [--db <path>] [--status <status>] [--workspace <id>] [--tab <id>] [--name <name>] [--raw] [summary|workspaces|tabs|panes|agents]` reads that database and prints a short tab-separated table. It does not call herdr and does not write the database. The default view is `summary`.

The path uses the same precedence as `sparks herdr snapshot`. A missing database exits 1 with one stderr line and creates nothing. Reads use a read-only immutable SQLite URI to avoid creating or updating sidecars. Pending WAL or rollback-journal data, or a database changed during the read, exits 1 rather than returning a stale or torn snapshot; retry after the writer closes.

`summary` prints the snapshot time and stored counts, then agent status counts, then one line for each agent whose status is not exactly `done`, even with filters. The other views print that table only. Columns are the parsed list fields, not the stored fetch JSON. `--raw` prints each stored fetch object on its own line instead; it does not apply to `summary`.

Filters are exact and combine. A filter that does not apply to the view is a usage error (exit 2). Zero matches still exit 0.

### `sparks agent spawn`

`bin/sparks agent spawn <type> [--prompt "<text>"] [--watch <seconds>] [--additional-flags "<string>"] [--timeout <seconds>] [--dry-run]` launches one agent persona as a pi session in a new herdr tab, in the current directory. Every persona runs in pi. The command is a thin wrapper over `herdr agent start <name> --kind pi -- <pi arguments>`: everything sparks adds (the model, the thinking level, tools, MCP, skills, and the system prompts it injects) is a pi argument, mapped from the persona's keys to the flags pi documents in `pi --help` and in its package docs, `docs/cli.md`: "Tools" (`--tools`, `--exclude-tools`, `--no-tools`, and "MCP tools"), "Resources" (`--no-mcp`, `--skill`, `--no-skills`, `-e`), and "Prompts and process" (`--append-system-prompt`, which appends text or an existing file's contents and is repeatable). [`docs/house/pi/prompt-construction-matrix.md`](docs/house/pi/prompt-construction-matrix.md) records how repeated appends join.

Personas live in `.sparks/agents.toml`: one TOML table per persona, named by the persona's id. The golden example [`defaults/agent.toml`](defaults/agent.toml) defines every key in its comments and carries commented examples; the `agent-personas` skill (`/agent-personas`) creates a project's file from it and maintains it. The command uses the nearest `.sparks/agents.toml`: the current directory first, then each parent up to the git top level (the first directory with a `.git`), or up to the filesystem root outside a git repository. It refuses a file, or a `.sparks` directory, that another user owns or that group or others can write, so a shared parent such as `/tmp` cannot supply a persona. A name that file does not define, or a missing file, falls back to the personas the plugin ships in [`defaults/agents.toml`](defaults/agents.toml); a project table with the same name replaces the shipped one. An unknown type is refused with both lists of names.

| Key | Required | pi argument |
|---|---|---|
| `role` | yes | none; for people and skills |
| `model_type` | yes | the chain of `--provider`/`--model`/`--thinking` combos below |
| `model`, `effort`, `provider` | no; `effort` with `model` | tried first, before the type's combos |
| `allowed_tools` | no | `--tools <list>` (with `allowed_mcp` entries); `[]` is `--no-tools` |
| `forbidden_tools` | no | `--exclude-tools <list>` (with `forbidden_mcp` entries) |
| `allowed_mcp` | no | `mcp__<server>__*` entries in `--tools`; `[]` is `--no-mcp` |
| `forbidden_mcp` | no | `mcp__<server>__*` entries in `--exclude-tools` |
| `skills` | no | `--no-skills`, then `--skill <dir>` for each; `[]` loads none |
| `allowed_directories` | no | an instruction in `--append-system-prompt` only; **pi does not enforce it** |
| `system_prompt` | no | `--append-system-prompt <text>` |
| `name`, `agent` | no | none; `name` must equal the table name, `agent` may only be `pi` |

- **Tools and MCP.** Tool entries are names or `*` patterns, with no `+name`/`-name` entries and no `mcp__` entries. MCP entries are server names, sent as `mcp__<server>__*` (characters other than letters, digits, and `_` become `_`, as pi names MCP tools), or `mcp__` patterns. pi keeps every MCP tool unless a `--tools` entry starts with `mcp__`, and `--tools` replaces the default tools, so a non-empty `allowed_mcp` needs `allowed_tools`. A tool or server both allowed and forbidden is refused. When either `allowed_mcp` or `forbidden_mcp` is set (even empty), `allowed_tools` entries containing `*` or `?` are refused to prevent wildcard bypass. The cross-server resource tools `list_mcp_resources`, `list_mcp_resource_templates`, and `read_mcp_resource` are excluded by default under these policies. **Resource opt-in:** explicitly list a resource tool by its literal name in `allowed_tools` to retain it; this permits access to resources on **all enabled servers**, not just allowed servers. Server-name policies cannot filter resource tool arguments; do not opt in if server isolation matters.
- **Skills.** Each name is looked up, first match wins, in `.pi/skills/<name>` and `.agents/skills/<name>` from the current directory up to the git top level, then the plugin's `skills/<name>`, then `$PI_CODING_AGENT_DIR/skills/<name>` (default `~/.pi/agent/skills`) and `~/.agents/skills/<name>`. An unknown name is refused, and so are skills when the persona allows neither `read` nor `bash`, because pi lists skills only when one of them can load them. The sparks skills set `disable-model-invocation`, so pi does not offer them to the model on its own: start the work with `/skill:<name>` in `--prompt`.
- **Directories.** pi has no sandbox (its docs say project trust "does not sandbox tool calls"), and no flag limits the directories a tool touches. `allowed_directories` is passed as an instruction in the system prompt and is not enforced. Run pi in a container for a real boundary.
- **The sparks prompt.** Every launch gets `--append-system-prompt` with the prompt all spawned workers share: read the `sparks.json` of every directory it will read or write and its parents; a `sparks.json` answer wins over the persona and its skills, and the conflict is named in the final report; at the end of its task, verify the diff just in time against the repository-root `sparks.json` and the `sparks.json` of every directory that holds a changed file, and quote each violated spark. Write a task-scoped verification skill checklist/procedure in a confirmed gitignored location (for example `.sparks/verify/<task>.md`), run it, and report its path, commands, and results, scoped to root plus touched subdirectory sparks and applicable ancestors. This adds no unrelated skills to pi. A read-only or directory-restricted worker must provide the procedure with an explicit handoff to the summoner to persist/run it, reporting the artifact as blocked rather than created. Then come the `allowed_directories` instruction and the persona's `system_prompt`, each its own `--append-system-prompt`; pi joins them with blank lines. Because an `--append-system-prompt` is always passed, pi's `APPEND_SYSTEM.md` (`.pi/APPEND_SYSTEM.md` or `~/.pi/agent/APPEND_SYSTEM.md`) never applies to a spawned persona: pi reads it only when no `--append-system-prompt` is given. pi's `SYSTEM.md` is not affected. Each prompt is one line with no tabs, because herdr refuses to type a control character into the shell, and must not be the path of an existing file, because pi would read that file instead.

#### Model types and fallback

Every persona names a `model_type`. [`defaults/model-types.toml`](defaults/model-types.toml) ships three: `powerful` (Claude Opus 5.5 high, then GPT-6.1 Sol high on `openai-codex`), `value` (Claude Sonnet 5.5 medium, then Grok 4.7 medium), and `fast` (Claude Haiku 5.5 low, GPT-5.3 Codex Spark low, Grok 4.3 low). Each type is an ordered list of combos, each a pi `provider`, `model`, `effort`, and optional `service_tier`, plus `fallback`, the other types to try after it: `fast` escalates to `value` then `powerful`, `value` to `powerful` then `fast`, and `powerful` falls back to `value` then `fast`. A project adds types or replaces one whole in `.sparks/model-types.toml`, found and owner-checked like `.sparks/agents.toml`. Users can add as many types as they want.

The chain for a launch is the persona's own `model` (when set), then its type's combos, then each fallback type's combos (not their own fallbacks, so a chain cannot loop); a repeated combo is dropped. spawn runs `pi --list-models` once and marks each combo available or not. Available combos are also deduplicated by resolved provider, model ID, and normalized pi thinking level, keeping the first occurrence (including a provider-omitted explicit model or equivalent effort spellings). It then tries the available combos in order: a combo whose `herdr agent start` fails has its tab closed, and the next combo gets a new tab and agent name. Every attempt is reported. If none starts, the command exits 1. `service_tier` is shown in the plan and attempts but not applied: pi has no service tier flag or setting.

#### API errors: the bundled pi extension

An API error (a rejected key, an overloaded provider, an unknown model) drops pi to idle, which herdr shows like a finished turn. [`pi/extensions/sparks-api-error-blocked.ts`](pi/extensions/sparks-api-error-blocked.ts) adds a per-run completion protocol. It publishes `sparks_run = "<seq>:ready"` at session start, increments the sequence only on the first `agent_start` of a logical run, and retains it across automatic retry/recovery/queued-work continuations until `agent_settled`. Each start clears `sparks_api_error` and republishes `<seq>:running`; settlement publishes `<seq>:ok`, `<seq>:error`, or `<seq>:aborted`. Error metadata includes `sparks_api_error`, only a provider/HTTP-status category plus the fixed message `api error: model request failed`. No provider diagnostic text is copied into tokens, labels, or spawn output; detailed diagnostics remain in the original local pi view. Only after metadata is acknowledged does it emit `herdr:blocked` with `sparks:api-error: <safe category and message>`; herdr's managed `herdr-agent-state.ts` reports the pane as blocked. The next run clears the API-error block. A rejected/missing metadata acknowledgement is reported as unconfirmed, not success. The managed herdr extension is not modified.

spawn always passes `-e <plugin>/pi/extensions/sparks-api-error-blocked.ts`, so this works without installing anything. To get it in every pi session, copy or symlink the file into `~/.pi/agent/extensions/` (this is the install step for `setup-sparks`). `-e`, `--extension`, `--no-extensions`, and `-ne` are refused in `--additional-flags`.

An API error only shows on a request. With `--prompt "<text>"`, spawn reads the run baseline, sends the text with `herdr agent prompt <pane> <text> --wait --until idle --until blocked --until done`, and polls `herdr agent get` within `--watch` seconds (more than 3, at most 300, default 60). It waits for the **current run's** terminal marker, never trusting an early idle/blocked state or a stale marker. A confirmed error closes the tab before retrying the same prompt with the next combo; a confirmed ok succeeds. Approval blocks (including a rejected `agent_blocked` prompt without an API-error token) keep the tab and exit 1 without fallback. Missing metadata, failed delivery/queries, aborted runs, submission/transport failures, and agents still working when the budget expires also keep the tab and exit 1 as failure-to-confirm, rather than silently succeeding or retrying a potentially live task. These responses include `attempts` and `left_open`. Without `--prompt`, only a failed start falls back.

```sh
cd path/to/project
path/to/sparks/bin/sparks agent spawn reviewer --prompt "/skill:spark-verification PR 91"
# {"agent": "reviewer-3f1a", "tab": "w1:t4", "pane": "w1:p7", "command": ["pi", "--provider", "anthropic", ...], "model_type": "powerful", "combo": {...}, "attempts": [...]}
```

- `effort` is `none`, `minimal`, `low`, `medium`, `high`, `xhigh` (`extra high`, `extra-high`, and `extrahigh` are the same), or `max`. `none` is sent as `off`. `ultra` is refused because pi has no ultra level, and a model pi lists without thinking only takes `none`. A model has no `:<thinking>` suffix and no speed word such as `fast`. Without a `provider`, the persona's own model is refused when more than one pi provider serves it.
- `--additional-flags` takes one string, split on whitespace, with each word appended to the pi command; quotes and backslashes are ordinary characters. It is refused if it holds a flag the persona sets (`--model`, `--models`, `--provider`, `--thinking`, `--effort`, `--speed`, `--system-prompt`, `--append-system-prompt`, `--tools`, `-t`, `--exclude-tools`, `-xt`, `--no-tools`, `-nt`, `--no-builtin-tools`, `-nbt`, `--no-mcp`, `--skill`, `--no-skills`, `-ns`), an extension flag (`-e`, `--extension`, `--no-extensions`, `-ne`), a flag that stops pi running interactively or makes it exit (`-p`, `--print`, `--mode`, `--export`, `--list-models`, `-h`, `--help`, `-v`, `--version`), or `--api-key`, which would show the key in the command, the pane, and the output. Other pi flags pass through. Pass it once, spelled in full.
- The launch runs `herdr tab create --cwd <cwd> --no-focus` (in `$HERDR_WORKSPACE_ID` when set), then `herdr agent start <name> --kind pi --pane <pane> --timeout <ms> -- <pi arguments>`. The agent name is the persona name, a hyphen, and four random hex digits. `--timeout` is herdr's start timeout in seconds, sent as whole milliseconds: more than 3000 and at most 300000 ms after rounding, default 30 seconds. Success prints one JSON line with `agent`, `tab`, `pane`, `command`, `model_type`, `combo`, and `attempts`.
- A failed start prints herdr's output and the pane's last 120 lines to stderr, then closes the tab. A tab herdr cannot close stops fallback immediately with exit 1, `attempts`, and `left_open`; no second agent is started. If every combo fails, the JSON line has `agent: null`, the `attempts`, and `left_open`. If `herdr tab create` succeeds but its reply has no tab and root pane, the `sparks: ` line names any tab herdr reported, which stays open.
- `--dry-run` checks everything, including `pi --list-models`, and prints the plan as one JSON line without calling herdr: `agent`, `config`, `model_types` (the files read), `cwd`, `model_type`, `chain` (each combo with `available`, a `reason` when it is not, and its `command`), `chosen`, `command`, and `timeout_ms`, plus `prompt` and `watch_ms` with `--prompt`.
- Exit 0 means launched (with a confirmed ok outcome when prompted), or the plan was printed. Exit 1 means refused with nothing launched, no combo available, every combo failed, cleanup failed, an approval block, or failure-to-confirm; kept tabs are named in `left_open`. Exit 2 is a usage error, including a `--timeout` or `--watch` out of range and `--watch` without `--prompt`.

The checks, the effort mapping, the provider rule, and the herdr launch are adapted from `gstack spawn` in [gdsrvnt/gstack](https://github.com/gdsrvnt/gstack), routed to pi only. There is no command yet to list or stop the agents it launched.

## Background

The point of spark is to improve context engineering in three ways that no existing paradigm achieves.

### Human prose is primary

#### User and human prose

There's a lot of craft encoded in the prose of highly technical or skilled humans, and the more of this voice exists in the context window of an agent working on any task, the better the agent adheres to desired behaviors.

One of the shortcomings of current approaches to context management is that the sources of context that are created, whether they are AGENTS.md files, some other kind of knowledge store, or even documentation, is not written by the engineers who commissioned the creation of such documents by agents. This is degenerate; because a human being passes understanding to agents in the form of prose which is then compiled into context files by an agent. This process is doubly lossy:

1. Summarization and paraphrasing are always lossy.

2. The assumptions and understandings underpinning the assertions themselves are typically not preserved by agents when creating or maintaining docs because *agents care more about what is than how it became*.

   and thus, even if the human practitioner encodes the rationale for certain facts into their communication of those facts to an agent, the agent typically strips them from the final product, and because it is rare that humans review that final product, since they instead prefer to rely on their skills, framework, model, harness, and workflow, those facts are not only lost, but worse yet, it is rarely detected that the facts are lost until it is too late. And then, invariably, some agent makes an error down the line. Then the human comes back and wonders why it is that the agent did not behave in the desirable fashion.

This is problematic because the same state in two projects, if a change needs to be made, are not treated the same by each team if the paths to that same state were radically different, and this changes the desirable behavior of agents in each project.

> Understanding how things came to be the way that they are is important for projecting current truth onto future action.

spark addresses this in 2 ways.

### 1. spark is verbatim-driven

The verbatim prose of a human being is an asset. spark persists context as user prose, whether out of written session transcripts or voice session transcripts over calls. The prose itself is elicited out of the user by specific means or mined  from transcripts and discussed cooperatively.

spark leans on the human practitioner to give clear, unambiguous and confident statements about the project. In so doing, *it demands more of the user than any other framework*.

> Agents tend to copy the conventions, rigor, and semantics of surrounding code when working in codebases. Since they think in *prose*, surround them with yours, and they will mimic the patterns of your reasoning organically.

### 2. spark encodes context as Question-Answer pairs

spark makes pieces of context and truths about the project easier to correlate by representing them as QA pairs. Existing context-management paradigms give an agent information, but because the agent does not know what gave it rise, it does not act on it desirably when judgment in correlating facts is required at implementation time. By representing context as QA pairs, spark natively binds rules to rationale, decisions to their assumptions, and facts to their relevance.


## Why use spark

Reason number one. Most excitingly, spark presents a new way to scale the performance of agents regardless of their harness, organization-wide or for the totality of an individual user's workflows. The reason for this is that spark allows any person or organization to build a moat of skill that is not easily acquired by other entities and only compounds into improved model performance in any application, in any project. The new access that spark unlocks is indeed the aspect of eloquence itself.

spark unlocks the capacity to build the moats and out-competes rivals along an axis that has hitherto been unharnessed.

In most industries, current state, the root of many organizations is already maximized or at the very least close to the maximum value that it should responsibly have because at the end of the day, organizations are limited now, not by what's creatable and generatable and producible, but as a matter of fact, by what is reviewable.

And so, one of the axes that organizations and teams that have levered is number one, how good material is before it gets to the review stage in the first place, since it reduces the length of the review phase and thereby increases productive throughput, but they are also limited by the way that the rate at which such output can be generated.

Furthermore, many teams rely on rigid, albeit effective, frameworks like to ensure that even at volume, agents produce desirable results with minimal human review. However, not unlike the problem with LLMs themselves, this results in a flattening or sanding down of the extremities where taste, craft, skill, opinion, and expertise emerge.

Furthermore, in an age where the vast majority of content, copy, and code is agent-generated, the premium on human-generated content will only get higher and higher, and indeed, it may be at a century high right now, and perhaps at the highest high since more than 90% of the population could read.

Teams have a vested interest in both the quality and the throughput of human output, since retaining verbatim human-generated text only pays off when it's produced at the highest rate and quality possible, while minimizing the attention cost of cleaning it for disfluencies and making it sound shippable. And thus, the more well-spoken the team becomes to the agent, and the better the team can develop its members along the aptitude curve of distilling intent into precise language quickly and at scale, the more equipped that team becomes to out-compete all others in its niche and indeed unlock the full potential of the technology.

<details>
<summary>A musing: the jockey on race day</summary>

> At a derby on race day, the only skill that matters for the jockey is their ability to drive the horse. Everything else is auxiliary to that access and occurs every day with painstaking and mind-blowing meticulousness from selecting suppliers of the horse's stock, in other words, the model's intelligence, to grooming the horse so that it's in the best mood on race day too, just as we groom, engineer, and manicure our content relentlessly. And yet, all of these are beginning to be treated as ends when indeed they are means to creating a track just like the one at the derby, along which we wish that our trusty steed will race in a fashion outperforming the others. But again, the wrong jockey on race day could lay waste to the team's hard work wholesale. And so in a similar sense, to train teams on becoming better expressed and invest in the linguistic proficiency of oneself and one's team is akin to training the body of the jockey and investing in him or her. Sparks gives teams a way not only to benefit from what capital they already have within their humans in that regard, but also to evaluate teams and train them on deepening this critical proficiency.

</details>

However, even more of the team's interests lie, and the interests, and the teams have more to gain in creating pipelines, not by which the models can distill intent into action anymore, but indeed in the pipelines by which intent and reasoning patterns are distilled into the agent's context to begin with. And so whether across a long-running solo project or any length of time in a project with a large team, the very reasons for which those individuals are on that team make it in the best interest of the team, and indeed apply, imply already that it is the intent of the team, the expertise, craft, takes decision-making, and rationale of those people is distilled in the behavior of the agents. Indeed, when any organization requires, requests for so much as permits the use of agents by their team, it is on the unspoken assumption that those agents will act in accordance with the proficiencies and aptitudes of the team members. However, in most ways, this promise is yet to be delivered faithfully by agents today.

spark already fixes this by distilling context only in the verbatim prose of human beings, and this has two marked benefits. Number one, it requires human practitioners to guard the context more closely and indeed compels them to create the context themselves. Number two, it gives all practitioners a channel through which to develop professionally that will in all likelihood become only more salient as all industries lean more and more heavily on the use of agents.

spark is very difficult to use at first. This is because it requires the human either to type long and detailed responses, or the human must dictate those responses in a fashion that is expressive, unambiguous, detailed, formal, and correct. Whereas currently, most workflows and working styles that incorporate dictation lean on the dictation software itself to clean disfluencies, and some of them even go so far as to write the dictation completely, which again is doubly degenerate on top of the degeneracy that has already been discussed, which arises from the current paradigms of context engineering in the first place.

At the end of the day, the entire point of context engineering is to preserve human intent in codebases, projects, and other workspaces. However, human intent is not more clearly expressed anywhere than in the verbatim words of human beings themselves. And thus, by demanding from the human being, or at the very least, making it highly advantageous for the human being to better express intent in prose, and then using that prose to guide any project or codebase, spark gives teams the avenues to improve compoundly with time, provided that the skill set spark requires is honed. Luckily, the very skill set spark requires today, to the exclusion of most other paradigms, will tomorrow be the expectation and most universally prized and desirable skill for most professionals working with agents.

## How spark works

By grouping context into categories and question answer pairs, it makes it easier for the agent to determine what matters. spark is highly opinionated about what it is that matters. It also makes it easier for the agent to elicit such things from the user using skills like `/study`.

### sparks.json

spark files represent context as question and answer pairs. The question can be asked by an agent or seeded by a human to encode even more intent.

I believe that intent can be encoded more strongly in prose that takes it as assumption than prose that asserts it. And so, for example, instead of saying what are the things that never should be done when resolving merge conflict, and then answering it in human prose, and thereby using the question mainly as a dumb marker for that piece of information, spark wants teams to do things like say, why is insert name of practice here always avoided in this repository when resolving merge conflicts? And then in the answer, human prose expressed in the most poignant way possible about exactly why. And thus, spark, by encouraging the encoding of context using QA pairs like these in their hundreds and thousands, helps things to compress context and intent into vastly fewer tokens while requiring less SaaS services and context management plumbing.

sparks.json files in any directory apply globally to a project by default. The user decides if and how to scope them for certain tasks.

A `sparks.json` list includes any number of sparks, JSON objects with a `type` of "s", "p", "a", "r", or "k", a `question`, an `answer`, and an optional `id`. The CLI accepts any case for `type` and writes lowercase.

### spark types

#### S: Stack and Implementation

The S stands for Stack and Implementation, and sparks of type S address the actual stack constituents, the tooling, the dependencies, the build pipelines, the production infrastructure, and other things pertaining to the plumbing and the nuts and bolts of the project itself; they answer architecture questions too. They're question answer pairs relating to the stack of the project. Again, optional.


#### P: Processes and Execution

Everything that is created is created for a purpose and is intended to have an effect on those who interact with it. The P, which stands for Processes and Execution, is the subset of sparks that answer questions about the shape the project has and the physical space it takes up in the world. The shape that it expresses to the world and or the effect and appearance that it should have on the public and those who see it. Like with every other type of spark, the question answer pairs need not only pertain to the desired production shape, but also may pertain to what should not be the shape and what sentiments and impressions should the product or project not leave on those who observe it.

How is this packaged, branded, presented and shipped? Why, when, who, where <all of those things>?

#### A: Audience and Visuals

This section, or rather, this type of spark is of course closely related to type P. Indeed, type A is the means by which the type P sparks are achieved, and thus P informs A, and A necessarily has consequences for P. Because this is the type of spark most heavily influenced by taste of the team and nature of the project, it is also the one whose conventions are least strict, if it can be said that any of the spark types have conventions at all.

In a sound engineering project, for example, the type A sparks will include a lot of information about the desired vibe of the sound or beats that the project is producing. If, for example, it is a AI generation, AI generated music project that uses Suno, then things like the preferred BPMs for certain types of music may be encoded here, in addition to what types of instruments should and should not be used. On the other hand, if the project pertains to the backend of a big data pipeline, then there likely would not be very much to the A section at all. However, that is not to say that such a project would have no sparks in A. It is simply to say that the sparks in A are to be shaped by whatever it is the team or practitioner perceives as art in the first place. And since the very definition of art is subjective, whereas in other contexts the definition of a thing is not subjective, but what actually constitutes such a thing is subjective.

The P sparks should also answer exactly who it is who will observe this in production and how they feel about it. Furthermore, it should answer questions about who it is that this project will be marketed to. Who is it that will be told about this project? Who is it that cares about this project and will be judging something based on this project and its quality? And also, how is it that this project will be evaluated and perceived?

What exactly to include in A is not advised upon herein at all.

Facts about the sensory footprint of the project.

#### R: Reconnaissance and Restrictions

This type of spark addresses the hard do not dos of a project, and in addition, it includes admonitions about what to be weary of of the project. What to be weary of when working on the project that cannot be documented as a hard rule as such because there is no substrate for it to prohibit, but rather just things that should be avoided or certain patterns that are not desirable, or clear question answers about what is not or what things are not or what should not come to be.

Reconnaissance is an ever-evolving subset of sparks that tracks the changing topology of the niche or domain or science of the project, and stores bits of context that are both important and liable to change quickly, whether to the advantage of the project or to its detriment.

#### K: Knowledge Sources

K is the last one. And K is one of the most powerful types of spark. K is Knowledge Sources. It doesn't just enumerate knowledge sources and leave the agent to do with them what it will. No. K is very useful because it allows a knowledge source to be assigned more than one job, but for that to be done very gracefully and depending on the question and the QA pair that holds a knowledge source. The agent knows how to query a particular knowledge source for a particular task at that particular moment in time. It increases the accuracy of when agents pull context from non-spark sources, and it also improves how agents query those sources once they get to them, which is way better than using index files, which most context management systems rely on right now.

### Five types of data

spark also helps to keep a project on the rails because it encompasses the five things that are most important about project management. It's five types of data at large that together make up pretty much all the domains of data that a project needs to have.

## Contributing

Every issue and every open pull request needs exactly one priority label: `low`, `medium`, `high`, or `urgent`. Draft PRs are exempt. See [CONTRIBUTING.md](CONTRIBUTING.md). Pull request text: [AGENTS.md](AGENTS.md).

## Credits

- [Lauren Tan (@poteto)](https://github.com/poteto), who wrote the pstack skills in this plugin: `ketchup`, `how`, `why`, `bro`, `create-verification-skill`, and `maintain-verification-skill`. Those last two are bundled for direct use; `spark-verification` is a separate read-only skill that checks a PR or branch against `sparks.json`.
- [Matt Pocock (@mattpocock)](https://github.com/mattpocock), whose `grilling` skill is the basis for the grilling core of `sparks-discuss`, whose `domain-modeling` skill is the basis for `sparks-domain`, and whose `to-spec` skill is the basis for `sparks-postcall`.
- [Yann Collet (@Cyan4973)](https://github.com/Cyan4973), who created [xxHash](https://github.com/Cyan4973/xxHash). `spark_hash.py` is a Python port of its XXH64 algorithm.

## License

MIT. Copyright (c) 2026 gdsrvnt. See `LICENSE`. That license covers this project's own work.

Third-party skills keep their authors' copyright and MIT licenses. Lauren Tan's skills are MIT, Copyright (c) 2026 Lauren Tan. `create-verification-skill` and `maintain-verification-skill` each carry her license in a `LICENSE` file next to their `SKILL.md`, and her other skills share `skills/LICENSE-poteto`. Matt Pocock's license is in `skills/LICENSE-mattpocock`, and `sparks-domain` and `sparks-postcall` each also carry it in a `LICENSE` file next to their `SKILL.md`. HumanLayer's license is in `skills/LICENSE-humanlayer`. `spark_hash.py` ports XXH64 from Yann Collet's xxHash, BSD 2-Clause, Copyright (c) 2012-2021 Yann Collet; its license is in `LICENSE-xxhash`. See `THIRD_PARTY_NOTICES.md`.

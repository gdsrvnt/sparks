# Pi prompt construction: provenance and override matrix

Verified against installed `@earendil-works/pi-coding-agent` **1.0.4**. This is a versioned implementation reference, not a promise about all Pi releases. Read the [developer handout](prompt-construction-handout.md) for the mental model and extension trust checklist.

## Paths and assumptions

- `<PI>`: installed package root; on the inspected machine, `/Users/godservant/.nvm/versions/node/v22.23.2/lib/node_modules/@earendil-works/pi-coding-agent`.
- `<A>`: agent directory, normally `~/.pi/agent`; override with `PI_CODING_AGENT_DIR` or SDK `agentDir`.
- `<CWD>`: working directory; project configuration is `<CWD>/.pi`.
- Implementation paths below are relative to `<PI>`. Upstream source counterparts replace `dist/` with `src/` and `.js` with `.ts` under `packages/coding-agent/`.
- Empty/nonempty columns assume `SYSTEM.md` is the selected source, without extension overrides. Project `SYSTEM.md` and `APPEND_SYSTEM.md` require trust. Context-file discovery does not.

## Section provenance and survival

| Section | Stock source / provenance | User customization | Trusted project scope | Selected `SYSTEM.md` is zero-byte | Selected `SYSTEM.md` is nonempty | Extension customization |
|---|---|---|---|---|---|---|
| `preamble` | Literal in `dist/core/system-prompt.js`, `buildSystemPromptSections()` | `<A>/SYSTEM.md` supplies `customPrompt` | `.pi/SYSTEM.md` replaces global source; not combined | Default stays | Default replaced by file contents | Assign `customPrompt`; `sections.preamble` is invalid |
| `tools` | Same builder, from registered tool `promptSnippet`; built-ins in `dist/core/tools/*.js` | Tool selection indirectly changes list; no generic snippet-length setting | `defaultTools` follows selection semantics below | Stays | Default omitted | Edit `toolSnippets`, or replace with nonempty `sections.tools` |
| `rules` | `buildRules()` in same file: selection rule, tool guidelines, extra guidelines, fixed defaults | No documented `settings.json` key for arbitrary rules; use instruction files or extension | Context instructions accumulate separately; not a rules override | Stays | Default omitted | Tool `promptGuidelines`; mutate `toolGuidelines`/`promptGuidelines`; nonempty `sections.rules` replaces whole section |
| `docs` | Literal in same builder; paths from `dist/config.js` | Custom prompt suppresses default | Project custom prompt has same effect | Stays | Default omitted | Nonempty `sections.docs` replaces/reintroduces |
| `addendum` | `appendSystemPrompt`, loaded by `dist/core/resource-loader.js` | `<A>/APPEND_SYSTEM.md` or CLI append input | `.pi/APPEND_SYSTEM.md` replaces global append-file source, but its contents append to the prompt | Included if supplied | Included if supplied | Assign/concatenate `appendSystemPrompt`, or override `sections.addendum` |
| `project_context` | `loadProjectContextFiles()` in resource loader; `renderProjectContext()` in builder | One candidate instruction file per directory | Global plus ancestor directories through CWD accumulate; not project-wins replacement | Included if loaded | Included if loaded | Mutate `contextFiles`, or nonempty `sections.project_context` replaces rendered section |
| `skills` | Discovery through loader; formatting in `dist/core/skills.js` | Discovered/configured skill metadata, not full skill bodies | Project and user resource paths load together, subject to resource identity/filtering | Included if eligible | Included if eligible | Mutate `skills`, or override `sections.skills` |
| `cwd` | Builder's `cwd`, backslashes normalized | Process/SDK working directory | Current directory, not an inherited setting | Stays | Stays | Mutate `cwd` or override `sections.cwd` |
| `mcp_servers` (example custom section) | Built-in extension `dist/extensions/mcp/index.js`, `renderServersSection()` and `before_agent_start` hook | Server configuration in `<A>/mcp.json` | Trusted `.pi/mcp.json`; server resolution belongs to MCP, not prompt-file precedence | Included for eligible servers | Included for eligible servers | Hook sets `sections.mcp_servers` for enabled servers with indirect tools; deletes key if none |
| Other custom sections | `sections` map applied last by builder | No generic Markdown-file discovery per section | Depends on extension, not universal scope precedence | Included if supplied | Included if supplied | Nonempty values add new names or replace existing names; names must match `^[a-z][a-z0-9_-]*$`, excluding `preamble` |

**Exact custom-prompt boundary:** only default `preamble`, `tools`, `rules`, and `docs` are in the `if (customPrompt)` branch. Addendum, context, skills, cwd, and custom sections are processed afterward. Non-preamble sections get XML-like wrappers. Empty custom-section values are ignored, not deletion instructions.

**Blank-file trap:** the reader removes a BOM but does not trim. `""` falls back to defaults; `"\n"` or `" "` suppresses them. An empty trusted project file still wins discovery over a nonempty global file, then falls back to built-ins. Use uppercase `SYSTEM.md` for portability.

Skills require discovered entries and a selected `read` or `bash` reader (including one hidden behind another tool). Omitting prompt summaries does not disable executable tools or remove separately supplied tool schemas/descriptions.

## Configuration, composition, and precedence

| Input / mechanism | Replace or add? | Project versus user / other precedence | Implementation / documentation |
|---|---|---|---|
| CLI `--system-prompt <text\|path>` | Explicit source replaces automatic source discovery; existing path means file contents, otherwise literal text | Wins over both discovered `SYSTEM.md` files | Loader: `systemPromptSource ?? discoverSystemPromptFile()`; `docs/cli.md`, “Prompts and process” |
| SDK resource-loader `systemPrompt` | Same explicit-source mechanism; not a `settings.json` preference | Explicit source bypasses file discovery | `dist/core/resource-loader.js`; `docs/sdk.md` |
| SDK loader override callbacks | `systemPromptOverride(base)` replaces resolved custom-prompt input; `appendSystemPromptOverride(base)` returns replacement append list (spread `base` to retain it) | Run after source resolution, before section construction; not forced whole-prompt replacement | `DefaultResourceLoaderOptions`; `examples/sdk/03-custom-prompt.ts` |
| CLI `--append-system-prompt <text\|path>` | Repeated explicit inputs join with blank lines and append to constructed prompt | Explicit append sources bypass discovered append-file source; do not also load both global/project files | Loader and `dist/core/agent-session.js`, `_rebuildSystemPrompt()` |
| Instruction files | Add separate path-labelled context blocks; no semantic conflict resolution | Global first, ancestors root-to-CWD afterward. First readable candidate per directory: `AGENTS.override.md`, `AGENTS.md`, `AGENTS.MD`, `CLAUDE.md`, `CLAUDE.MD`. Override affects only that directory. Linked-worktree shadowing/deduplication avoids duplicate logical context | `loadProjectContextFiles()`; `docs/configuration.md`, “Context files”. `--no-context-files` disables discovery |
| Ordinary settings | Objects merge recursively; project scalar/leaf values and ordinary arrays replace inherited values | Trust gates project settings; global-only settings ignore project values; resource loading and `defaultTools` have special semantics below | `dist/core/settings-manager.js`, `deepMergeObjects()`/`deepMergeSettings()`; `docs/settings.md` |
| `defaultTools` | Plain names replace selection; `+name`/`-name` modify it | Project delta-only list modifies inherited user selection; any plain names establish replacement selection, then deltas apply in order | `docs/settings.md`, “Tools”. Empty array disables built-ins, not extension/SDK tools; CLI tool flags override |
| Resource arrays (`extensions`, `skills`, `prompts`, `themes`) | User/project resource paths load together; filters control inclusion | No blanket project replacement; builtin `+builtin:name`/`-builtin:name` project entries override user selection | `docs/settings.md`, “Resources” |
| Package declarations | Load bundled extensions/skills/templates/themes; manifest is not a declarative system-prompt override | Same package identity: project normally replaces user entry; `autoload: false` makes project entry a filtering delta | `docs/packages.md`, “Understand scope and identity” |
| Tool `promptSnippet` | Registration collapses whitespace to one line; normalized string inserted without length truncation; empty snippet omits list entry | Replacement tool definitions supply their own snippets/guidelines, not automatic inheritance from overridden built-ins | Session `_normalizePromptSnippet()` and builder. `codemode.inlineBudget` limits codemode's tool-description listing, not these snippets |
| Tool `promptGuidelines` | Active, nonhidden tools contribute bullets to default rules | Registration/hook behavior decides replacement; not instruction-file precedence | `dist/core/extensions/types.d.ts`; tool definitions |
| Hook `promptGuidelines.push(...)` | Adds bullets to default rules; all guideline sources trimmed/deduplicated | Hooks run in extension load/registration order; assigning arrays instead replaces that input collection | `before_agent_start`; `dist/core/extensions/runner.js` |
| Hook `sections.rules = "..."` | Replaces generated rules after construction; can reintroduce rules under custom prompt | Later hook assignments to same key overwrite earlier ones; no automatic project-wins policy | Builder and extension runner |
| Hook `forceSystemPrompt` or returned `{ systemPrompt }` | Replaces all constructed prompt text for that run, including context/skills/cwd/custom sections; `""` can force empty text | Shared options flow through ordered handlers; returned `systemPrompt` sets `forceSystemPrompt` | `docs/extensions.md`, “Events and concurrency”; runner `emitBeforeAgentStart()`; session `_installAgentForcedPromptProjection()` |

Forced projection retains current tool declarations and conversation, not constructed textual sections. It covers the accepted run, including tool follow-ups; run options clear when Pi settles, and hooks must reapply the override on future runs. Structured sections are still recorded/diffed in the transcript, so persisted prompt state is not sufficient evidence of the provider's actual forced text. Request-local `context_with_system` transformations can also change the outgoing transcript.

## Exact stock constructed prompt

Baseline: fresh session, normal default tools `read,bash,edit,write`, no user/project resources or instructions, no explicit prompt override, no MCP servers or extension changes. The CLI's built-in extensions load by default (`mcp`, `llama.cpp`, `codemode`, `tool-search`), but codemode/tool-search are inactive without configuration/activation; SDK sessions do not automatically load the CLI's MCP/codemode/tool-search extensions. The following is the builder's exact text with only installation paths and CWD replaced by placeholders. Tool schemas are a separate request channel, not reproduced here. Provider adapters may serialize structured system messages differently.

```text
You are an expert coding assistant operating inside pi, a coding agent harness. You help users by reading files, executing commands, editing code, and writing new files.

<tools>
- read: Read file contents
- bash: Execute bash commands (ls, grep, find, etc.)
- edit: Make precise file edits with exact text replacement, including multiple disjoint edits in one call
- write: Create or overwrite files

In addition to the tools above, you may have access to other custom tools depending on the project.
</tools>

<rules>
- Use bash for file operations like ls, rg, find
- Use read to examine files instead of cat or sed.
- You can inspect PI_* environment variables for current model and session details.
- Use edit for precise changes (edits[].oldText must match exactly)
- When changing multiple separate locations in one file, use one edit call with multiple entries in edits[] instead of multiple edit calls
- Each edits[].oldText is matched against the original file, not after earlier edits are applied. Do not emit overlapping or nested edits. Merge nearby changes into one edit.
- Keep edits[].oldText as small as possible while still being unique in the file. Do not pad with large unchanged regions.
- Use write only for new files or complete rewrites.
- Be concise in your responses
- Show file paths clearly when working with files
</rules>

<docs>
Pi documentation (read only when the user asks about pi itself, its SDK, extensions, themes, skills, or TUI):
- Main documentation: <PI>/README.md
- Additional docs: <PI>/docs
- Examples: <PI>/examples (extensions, custom tools, SDK)
- When reading pi docs or examples, resolve docs/... under Additional docs and examples/... under Examples, not the current working directory
- When asked about: extensions (docs/extensions.md, examples/extensions/), themes (docs/themes.md), skills (docs/skills.md), prompt templates (docs/prompt-templates.md), TUI components (docs/tui.md), keybindings (docs/keybindings.md), SDK integrations (docs/sdk.md), custom providers (docs/custom-provider.md), adding models (docs/models.md), pi packages (docs/packages.md), environment variables (docs/environment-variables.md), MCP servers (docs/mcp.md), codemode scripts and non-LLM models such as classifiers and image models (docs/codemode.md)
- When working on pi topics, read the docs and examples, and follow .md cross-references before implementing
- Always read pi .md files completely and follow links to related docs (e.g., tui.md for TUI API details)
</docs>

<cwd>
<CWD>
</cwd>
```

Stock rules are instructions to the model, **not enforced access-control policy**. Enforcement needs executable controls and/or OS isolation.

## Source index

Local authoritative evidence: `<PI>/dist/core/{system-prompt,resource-loader,agent-session}.js`, `<PI>/dist/core/extensions/{runner.js,types.d.ts}`, and `<PI>/dist/core/tools/{read,bash,edit,write}.js`.

Upstream links below track `main` and may drift from the inspected 1.0.4 installation:

- [Prompt builder](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/src/core/system-prompt.ts)
- [Configuration](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/configuration.md)
- [Settings](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/settings.md)
- [CLI](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/cli.md)
- [Packages](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md)

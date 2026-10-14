---
name: agent-personas
description: Create and maintain a project's agent personas in .sparks/agents.toml and its model types in .sparks/model-types.toml, the files sparks agent spawn reads to launch each persona as a pi session in herdr. Use for /agent-personas, "add an agent persona", "add a model type", or editing, removing, or checking the personas in .sparks/agents.toml.
disable-model-invocation: true
---

# agent personas

Keep a project's `.sparks/agents.toml` correct, one persona at a time. A persona is one TOML table: its name, a role, a model type, and optionally its own model, effort, and provider, allowed and forbidden tools, allowed and forbidden MCP servers, skills, allowed directories, a system prompt, and the agent that runs it. `sparks agent spawn <name>` turns that table into pi arguments and launches it in a new herdr tab. The same skill keeps the project's `.sparks/model-types.toml`, one model type at a time.

## The schema lives in three places

- [`defaults/agent.toml`](../../defaults/agent.toml) is the golden example. Its comments define every persona key, which are required, and the pi flag each becomes.
- [`defaults/model-types.toml`](../../defaults/model-types.toml) defines the model types (`value`, `powerful`, `fast`) and the keys of a type and its combos.
- [`defaults/agents.toml`](../../defaults/agents.toml) holds the personas the plugin ships (`spec-writer`, `implementer`, `reviewer`). spawn uses them when the project does not define that name.

Open them before every session. Don't work from memory, and don't restate their rules to the user in your own words: quote them. The `sparks agent spawn --help` text in [`bin/sparks`](../../bin/sparks) gives the same rules from the command's side. Where they differ, report it; don't pick one.

## Non-negotiables

- Decisions are the user's: the persona's name, role, model type, model, effort, provider, tools, MCP servers, skills, directories, and system prompt, and every model type and combo. Never pick one for them, and never fill a key the user did not give.
- Facts are your job. Look up what pi offers yourself: `pi --list-models <model>` prints the provider, the exact model id, and whether the model thinks. Never invent a model id, a provider, a tool, or a skill.
- One change per turn: add, edit, or remove one persona or one model type. Show the exact TOML table before writing, and write only after an unchanged yes.
- The role and system prompt are the user's words. Never paraphrase or tidy them. If one needs fixing, ask the user to restate it.
- Edit only that table. Keep every other table, comment, and blank line as it is.
- Never commit `.sparks/agents.toml` or `.sparks/model-types.toml`. Whether and where they are committed is the project's call.
- Never edit the plugin's `defaults/`. To change a shipped persona or type for one project, add a table with the same name to the project file. It replaces the shipped one whole.
- Say plainly that `allowed_directories` is an instruction in the system prompt and that pi does not enforce it.
- This skill never launches an agent. The check below is a dry run.

## First turn

1. Ask which project the personas belong to. The default is the current directory.
2. Look for `<project>/.sparks/agents.toml` and `<project>/.sparks/model-types.toml`. `sparks agent spawn` uses the nearest of each from the directory it runs in, walking up to the git top level (the first directory with a `.git`), or to the filesystem root outside a git repository. Say if a parent directory inside that range has one that would win for a subdirectory. spawn refuses either file if another user owns it or its `.sparks` directory, or if group or others can write either; report that as the check prints it.
3. If there is no `agents.toml`, say that spawn still runs the shipped personas, and offer to create the file: copy `defaults/agent.toml` there unchanged, creating `.sparks/` if needed, with neither writable by group or others. The copy has its comments and no personas. Write it only after a yes.
4. If there is one, read it and list each persona: its name, role, and model type, and any model and effort. Run the check below on each and report the result. List the shipped personas the project does not replace. Then ask what the user wants to change.

## Add or edit a persona

1. Ask for what is missing, one key at a time: the name, then the role, then the model type (list the types the check would see: shipped plus project). Then ask about the optional keys, in the golden example's order: its own model (with effort, and provider if needed), tools, MCP servers, skills, directories, system prompt.
2. Check the facts before you show the table:
   - The name follows the rule in the golden example. `sparks agent spawn` refuses others.
   - A model: `pi --list-models <model>` lists that exact id. If it lists more than one provider for it and the user gave none, say which ones and ask. If pi lists the model without thinking, say so: only effort `none` works for it.
   - The effort is one the golden example allows. Tell the user if it maps to another pi level (none is sent as off) or is refused (ultra).
   - Tools and MCP servers: say which pi flag each list becomes, as the golden example states. Say that a non-empty `allowed_mcp` needs `allowed_tools`, and that `[]` means none (`--no-tools`, `--no-mcp`, no skills). With either MCP key set, `allowed_tools` cannot contain `*` or `?`. The three cross-server resource tools are excluded unless explicitly named in `allowed_tools`; this opt-in grants resources on all enabled servers, not server-scoped access. Explain this limitation before offering resource access.
   - Skills: each name must exist where the golden example says spawn looks. List what you found and where. Say that the sparks skills are started with `/skill:<name>` in the first prompt.
   - A system prompt must fit the golden example's rule. If the user's prompt has line breaks, show it as a `"""` string with each line ending in `\`, which TOML joins into one line, and ask if that is what they want.
3. Show the exact table, the path, and whether it adds a persona or replaces one (old table, then new table). That is the turn's one question.
4. On a yes, write it. A new persona goes at the end of the file.
5. Run the check on that persona and report the result.

## Add or edit a model type

1. Ask for the type's name, then each combo in order (provider, model, effort, and optionally a service tier), then its fallback types in order.
2. Check each combo with `pi --list-models <model>`. Say that pi cannot apply a service tier: spawn records it but passes nothing.
3. Show the exact table with its `[[<type>.combos]]` tables, and whether it adds a type or replaces a shipped or project one. On a yes, write it to `.sparks/model-types.toml` (create it with the same ownership and mode rules as `agents.toml`).
4. Run the check on a persona that uses the type and report its chain.

## Remove a persona or type

Show the table that will go and ask. On a yes, delete the table and its comments, and nothing else. If it replaced a shipped persona or type, say that the shipped one applies again. A launched agent keeps running; removing its persona doesn't stop it.

## The check

From the project directory, run the plugin's `bin/sparks` (two directories above this file) for the persona:

```sh
<plugin root>/bin/sparks agent spawn <name> --dry-run
```

Exit 0 prints one JSON line: the agent name it would use, the config and model type files it read, the directory, the model type, the chain of combos (each marked available or not, with the reason), the chosen combo, the pi command, and the start timeout. Show the `chain` and the `command` to the user: the command is exactly what herdr would run first. Exit 1 prints one `sparks: ` line saying what is wrong. Report it word for word, then fix the table with the user, never around them. The dry run calls `pi --list-models` and never calls herdr. On Windows, run `uv run --script <plugin root>/bin/sparks agent spawn ...`.

A pass means pi can run at least one combo as written. It does not mean the provider is logged in or that its key works. At launch, a failed start or (with `--prompt`) an API error moves on to the next combo.

## Done

The user ends the session. When every persona passes the check, say so in one line and ask if there is another change.

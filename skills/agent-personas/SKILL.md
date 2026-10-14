---
name: agent-personas
description: Create and maintain a project's agent personas in .sparks/agents.toml, the file sparks agent spawn reads to launch each persona as a pi session in herdr. Use for /agent-personas, "add an agent persona", or editing, removing, or checking the personas in .sparks/agents.toml.
disable-model-invocation: true
---

# agent personas

Keep a project's `.sparks/agents.toml` correct, one persona at a time. A persona is one TOML table: its name, a role, a model, an effort, and optionally a provider, a system prompt, and the agent that runs it. `sparks agent spawn <name>` turns that table into a pi command and launches it in a new herdr tab.

## The schema lives in one place

The golden example is [`defaults/agent.toml`](../../defaults/agent.toml) in this plugin. Its comments define every key, which are required, and what pi does with each. Open it before every session; don't work from memory, and don't restate its rules to the user in your own words. Quote them. The `sparks agent spawn --help` text in [`bin/sparks`](../../bin/sparks) gives the same rules from the command's side. Where they differ, report it; don't pick one.

## Non-negotiables

- Decisions are the user's: the persona's name, role, model, effort, provider, and system prompt. Never pick one for them, and never fill a key the user did not give.
- Facts are your job. Look up what pi offers yourself: `pi --list-models <model>` prints the provider, the exact model id, and whether the model thinks. Never invent a model id or a provider.
- One change per turn: add, edit, or remove one persona. Show the exact TOML table before writing, and write only after an unchanged yes.
- The role and system prompt are the user's words. Never paraphrase or tidy them. If one needs fixing, ask the user to restate it.
- Edit only the persona's table. Keep every other table, comment, and blank line as it is.
- Never commit `.sparks/agents.toml`. Whether and where it is committed is the project's call.
- This skill never launches an agent. The check below is a dry run.

## First turn

1. Ask which project the personas belong to. The default is the current directory.
2. Look for `<project>/.sparks/agents.toml`. `sparks agent spawn` uses the nearest one from the directory it runs in, walking up to the git top level (the first directory with a `.git`), or to the filesystem root outside a git repository, so also say if a parent directory inside that range has one that would win for a subdirectory. spawn refuses the file if another user owns it or its `.sparks` directory, or if group or others can write either; report that as the check prints it.
3. If there is none, offer to create it: copy `defaults/agent.toml` there unchanged, creating `.sparks/` if needed, with neither writable by group or others. The copy has its comments and no personas. Write it only after a yes.
4. If there is one, read it and list each persona: its name, role, model, and effort. Run the check below on each and report the result. Then ask what the user wants to change.

## Add or edit a persona

1. Ask for what is missing, one key at a time: the name, then the role, the model, the effort. Ask about the provider and a system prompt; both are optional.
2. Check the facts before you show the table:
   - The name follows the rule in the golden example. `sparks agent spawn` refuses others.
   - `pi --list-models <model>` lists that exact id. If it lists more than one provider for it and the user gave none, say which ones and ask. If pi lists the model without thinking, say so: only effort `none` works for it.
   - The effort is one the golden example allows. Tell the user if it maps to another pi level (none is sent as off) or is refused (ultra).
   - A system prompt must fit the golden example's rule. If the user's prompt has line breaks, show it as a `"""` string with each line ending in `\`, which TOML joins into one line, and ask if that is what they want.
3. Show the exact table, the path, and whether it adds a persona or replaces one (old table, then new table). That is the turn's one question.
4. On a yes, write it. A new persona goes at the end of the file.
5. Run the check on that persona and report the result.

## Remove a persona

Show the table that will go and ask. On a yes, delete the table and its comments, and nothing else. A launched agent keeps running; removing its persona doesn't stop it.

## The check

From the project directory, run the plugin's `bin/sparks` (two directories above this file) for the persona:

```sh
<plugin root>/bin/sparks agent spawn <name> --dry-run
```

Exit 0 prints one JSON line: the agent name it would use, the config it read, the directory, the pi command, and the start timeout. Show the `command` to the user: it is exactly what herdr would run. Exit 1 prints one `sparks: ` line saying what is wrong. Report it word for word, then fix the table with the user, never around them. The dry run calls `pi --list-models` and never calls herdr. On Windows, run `uv run --script <plugin root>/bin/sparks agent spawn ...`.

A pass means pi can run the persona as written. It does not mean the provider is logged in; pi reports that when the persona is launched.

## Done

The user ends the session. When every persona passes the check, say so in one line and ask if there is another change.

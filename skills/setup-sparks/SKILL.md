---
name: setup-sparks
description: Set up sparks for voice calls. Install the VoiceBot, the bot teammate that handles the user's voice calls, from the VoiceBot template, check its rules and private voice skills, write pi's SYSTEM.md files, and install the sparks pi extension that reports API errors to herdr. The user runs /setup-sparks.
disable-model-invocation: true
---

# setup sparks

Set up the VoiceBot and the pi configuration that voice work with sparks needs. Do the steps in order and report what each one installed, reused, created, or skipped.

The VoiceBot is the bot teammate that handles the user's voice calls. It installs from the [VoiceBot template](https://x.ai/bot/GmSYdQGx5czseTDLcA2Ct), which carries its rules and its private skills: spark-voice for the call and voice-call-end for hang-up. The steps below say "the VoiceBot template" for that link.

`<plugin root>` below is the absolute path of the installed sparks plugin: the directory that holds `.cursor-plugin/plugin.json`, two directories above this file.

## 1. Install the VoiceBot

If the VoiceBot is already installed, defined, or spawned, reuse it. Otherwise tell the user to install it from the VoiceBot template, and wait until the user says it is installed.

## 2. Check the installed VoiceBot

The VoiceBot template is the source of truth. Confirm the installed VoiceBot carries these six rules:

```text
- You are the user's only voice-call bot.
- You work only during a voice call and immediately after it. Outside that window, don't route work, follow up, or relay teammate results; teammates report to the user directly.
- During a call, act as the user's chief of staff: relay the user's requests to teammates word for word with the send-task tool.
- Your voice skills, spark-voice for the call and voice-call-end for hang-up, are private to you. They never go in shared or teammate skills.
- Refer to the user as "the user", never by first name.
- At the end of every call, find the call transcript on your machine and send its path to every teammate you contacted during the call, with instructions to verify their work against specs mined from the transcript.
```

Also confirm that spark-voice and voice-call-end are its private skills, not shared or teammate skills.

Then confirm that both skills point at the sparks plugin's files where they live in the installed plugin, not at paths relative to the skill: `skills/sparks-postcall/SKILL.md`, `skills/sparks-discuss/SKILL.md`, and `bin/sparks`. Open every path the two skills name, and list each one that doesn't resolve with the skill that names it.

If a rule or skill is missing, a voice skill is shared, or a path doesn't resolve, tell the user rather than writing or editing it yourself.

## 3. pi workaround for Anthropic models

Do this step only if pi won't run Anthropic models because it is a third-party harness. A `SYSTEM.md` replaces pi's default system prompt.

Create `SYSTEM.md` in pi's agent directory, `~/.pi/agent` (or the directory `PI_CODING_AGENT_DIR` names). Its only content is exactly:

```text
Refer to the context of all sparks.json files you encounter to complete your work.
```

A non-empty `SYSTEM.md` also replaces pi's default tools, rules, and docs sections, so pi runs without its built-in tool guidance.

If a `SYSTEM.md` is already there, show it to the user and overwrite it only on their word. Then start pi again (or run `/reload`) and confirm an Anthropic model runs.

## 4. pi project directory in the VoiceBot's workspace

Always do this step, whichever models pi runs, so the pi coding agent behaves in the VoiceBot's workspace. Create a `.pi` directory at that workspace's root holding `.pi/SYSTEM.md` with the same single line as step 3. pi loads it in place of its default system prompt when it runs in that workspace, and it takes precedence over the agent directory's `SYSTEM.md`. As in step 3, it also replaces pi's default tools, rules, and docs sections there.

If an existing `.pi/` there is managed by something else, skip this step and say so. Otherwise the same rule applies: if `.pi/SYSTEM.md` already exists, show it to the user and overwrite it only on their word. pi loads a project's `.pi/SYSTEM.md` only after the user grants that project trust, so tell the user to accept the trust prompt the first time pi starts there.

## 5. sparks pi extension for API errors

The sparks pi extension `<plugin root>/pi/extensions/sparks-api-error-blocked.ts` marks a pi agent blocked in herdr when it hits an API error. A failed agent spawn then shows up as blocked, and the caller falls back. It sends that signal through herdr's own pi extension, `herdr-agent-state`.

Install it into pi's extensions folder, `~/.pi/agent/extensions/` (or `extensions/` in the directory `PI_CODING_AGENT_DIR` names), by copying it or symlinking to it as `sparks-api-error-blocked.ts`:

- If the source file is missing from the plugin, skip the install and report it skipped.
- If an identical file, or a symlink to the source, is already there, change nothing and report it already present.
- If a different file has that name, show the user the diff and overwrite it only on their word.

Then check that `herdr-agent-state.ts` is in the same folder. The blocked signal travels through it, so if it's missing, report that and suggest the user install herdr's pi integration (`herdr integration install pi`; `herdr integration status` shows it). Don't install it yourself.

pi loads extensions when it starts, so tell the user to start pi again (or run `/reload`) to load it.

## Report

End with one line per step: whether the VoiceBot was installed from the VoiceBot template or reused; which of the six rules and private voice skills the check found, anything missing, and each path that doesn't resolve; each `SYSTEM.md` path with created, already present, or skipped; and the sparks pi extension with installed, already present, overwritten, or skipped, plus whether `herdr-agent-state.ts` was found.

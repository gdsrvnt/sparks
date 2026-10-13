---
name: sparks-postcall
description: After a voice or phone call ends, extract a spec from the call transcript using only the user's own words, verify the work done during the call against it, implement the gaps, open the needed pull requests, have strong models review them, and push hard to merge low-risk, reversible changes. Use for /sparks-postcall, or when the user asks to turn a finished call into a spec and close out its work.
disable-model-invocation: true
---

# Sparks postcall

This skill turns a finished call into a spec, then audits and completes the work done during the call. It is adapted from Matt Pocock's `to-spec` skill. The spec template and the "synthesize, don't interview" stance come from his skill. The source changes from the live conversation to the transcript, and the skill then verifies the call's work, fills the gaps, and merges.

It is a self-healing loop. The call already said what the user wanted. Whatever was missed during the call gets fixed now, through reversible PRs, without another round of questions, unless something truly needs the user.

Agent work runs through [`use-herdr`](../use-herdr/SKILL.md). Open it now and follow it for every agent you launch.

## Non-negotiables

- **The user's words are the source of truth.** Every requirement cites at least one verbatim quote from the user. Never invent a requirement, and never upgrade an assistant or relay paraphrase into one.
- **Relays can garble.** Anything that passed through a relay, a summary, or speech-to-text may differ from what the user said. Use the user's own utterances. List every difference you find.
- **Do not interview during synthesis.** As in `to-spec`, write the spec from what is already there. Anything the transcript leaves undecided becomes an open question for the user. Do not guess.
- **Ask before anything irreversible.** Merging reversible work is the point of this skill. Deleting, publishing a release, force-pushing, or sending messages to other people is not. Those need the user's explicit approval.

## Process

### 1. Locate the transcript

Find the transcript for the call: the call log, the voice channel history, or a file the user names. Record where it came from and the start and end time of the call, with time zones. If there is no transcript or more than one candidate, stop and ask which call. This is the one question you may ask before the spec.

### 2. Extract the user's utterances

Copy out every utterance by the user, word for word, in order. Number them `U1`, `U2`, and so on, with a timestamp where the transcript has one. Leave out assistant turns, tool output, and relayed restatements.

Then build the **relay-divergence list**. For each relayed or summarized version of an instruction, compare it with the user's utterance. Record the quote index, what the relay said, what the user said, and whether the difference changes the meaning. Misheard names and words count, and so do dropped conditions, added scope, and changed numbers.

### 3. Write the spec

Explore the repositories the call touched, as in `to-spec`, so the spec uses the project's own vocabulary and respects its `sparks.json` entries. Then write the spec with this template:

<spec-template>

## Source

The transcript location, the call's time span, and the numbered user utterances (`U1`, `U2`, ...).

## Relay divergences

Each difference between a relay and the user's own words: quote index, relay version, user version, and meaning changed (yes or no).

## Problem Statement

The problem the user faces, from the user's perspective, citing quotes.

## Solution

The solution, from the user's perspective, citing quotes.

## Requirements

A numbered list, `R1`, `R2`, and so on. Each requirement is one testable statement tied to the quote indices it comes from. Nothing without a quote.

## User Stories

A long, numbered list of user stories in the form: As an <actor>, I want a <feature>, so that <benefit>. Each story lists acceptance criteria that can be checked against real artifacts, and the requirements it covers.

## Implementation Decisions

The decisions the user made on the call: modules, interfaces, naming, and constraints. Avoid file paths and code snippets, which go stale.

## Out of Scope

What the user ruled out, with quotes.

## Open Questions

Anything the transcript leaves undecided or contradictory, each with the quotes that raise it. These go to the user. They are never answered by guessing.

</spec-template>

Save the spec where the user keeps work notes. If the user asks for it on the issue tracker, publish it there.

### 4. Gather the work done during the call

Using the call's time span, with a margin for work that was started during the call and finished after it, collect everything produced in that window: commits, branches, pull requests opened and merged, issues, comments, and files changed in the affected repositories. Use `git log --since --until` and the forge's API or CLI. Record each item with its link and time.

### 5. Verify each requirement

For every requirement, mark it `met`, `partial`, or `missing`, with evidence: a commit, a PR, a file and line, or command output. A claim in chat is not evidence, and neither is a PR title. Check the real diff or the real file. Hand the verification to a strong reviewer through `use-herdr` when it is more than a few requirements, and check its evidence yourself before you accept it.

Present the table to the user along with the relay divergences and open questions.

### 6. Implement the gaps

For each `partial` or `missing` requirement that has no open question blocking it, launch an agent through `use-herdr` in a fresh worktree off the default branch tip, one agent per tab. Give it the requirement, its quotes, its acceptance criteria, and the project's identity and public-text rules. Group related gaps into one PR. Keep unrelated gaps in separate PRs.

### 7. Open the pull requests

Open one PR per coherent change. Each PR body lists the requirements it closes, with their quotes and acceptance criteria. Report every PR as its number and a link.

### 8. Review with strong models

Before merging, have each PR reviewed through `use-herdr` by a strong model at high effort. Use Claude Code with Opus at high or xhigh, or pi with a frontier xAI Grok or OpenAI model at high or xhigh. Use a different model from the one that wrote the change where you can. The reviewer checks the diff against the spec's requirements and acceptance criteria and reports findings by severity. Fix real findings and review again. Record a review that comes back clean.

### 9. Push to merge

Merging is the default outcome, not a favor to ask for. A gap the call left behind is a defect, and a reviewed, reversible fix is the low-risk way to heal it. Merge a PR (squash, as the configured bot identity) when all of these hold:

- the strong-model review is clean, or every real finding is fixed and reviewed again
- tests and checks are green
- the change is docs-only or otherwise easy to revert, and touches no secrets, releases, or destructive operations

If any condition fails, do not merge, and do not quietly let the PR sit either. Send the user one numbered message that names the single blocker for each PR, what you need from them, and the PR's number and link.

## Done

The skill is done when every requirement is `met` and merged, or is waiting on an open question or blocker the user has in one numbered message. The final report gives the spec location, the requirement table, the relay divergences, every PR's number, link, and merge commit, and the open questions.

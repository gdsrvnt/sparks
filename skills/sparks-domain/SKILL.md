---
name: sparks-domain
description: Run the Sparks interview with domain modeling built in. Challenge the project's terms, sharpen fuzzy language, stress-test concepts with scenarios, and check them against the code, then add or replace each settled term and decision in sparks.json with the sparks CLI. Use for /sparks-domain, or to build a project's domain language as Spark entries.
disable-model-invocation: true
---

# Sparks domain

This is the [`sparks-discuss`](../sparks-discuss/SKILL.md) interview with Matt Pocock's domain modeling built in. Use domain modeling to decide what to ask. Use sparks-discuss for how to ask it and where the answer goes.

Open [`../sparks-discuss/SKILL.md`](../sparks-discuss/SKILL.md) now and follow it in full: non-negotiables, personas, the 3-question reload, first turn, entry types, verbatim answers, the `/why` route, the add-or-replace protocol, and done. This file adds the domain-modeling moves on top. Where the two conflict, sparks-discuss wins.

Domain modeling is the *active* discipline. You challenge terms, invent edge-case scenarios, and capture the language the moment it settles. Reading the project's vocabulary is not this skill. This skill is for when the model is changing.

## Output goes into Sparks only

Every resolved term and every recorded decision becomes a Spark entry, written one at a time through `sparks entry add` under sparks-discuss's add-or-replace protocol. Nothing else is written.

- Never create or edit `GLOSSARY.md`, `GLOSSARY-MAP.md`, `CONTEXT.md`, `CONTEXT-MAP.md`, or `docs/adr/`. Never print a glossary or an ADR as the session's output.
- If those files exist, read them. They are sources to challenge against, the same as the code. Where `sparks.json` and one of them disagree, surface it as a question.
- `<dir>/sparks.json` is the glossary. Read it on the first turn (sparks-discuss's first turn already does). Treat its answers as the project's existing language.

## Domain moves

Each move produces a question. The question still follows sparks-discuss: open, one per turn, no options, no recommended answer, tagged with its type. A fact you found and show the user is fair game. A term or decision you put forward as the answer is not.

### Challenge against the sparks

When the user uses a term that conflicts with an existing answer in `sparks.json`, call it out on the next turn. Quote the stored answer, say what the user seems to mean now, and ask which holds and why. If the old answer is wrong, the fix is a replace of that record, after the user restates it.

### Sharpen fuzzy language

When a term is vague or overloaded, show where it's doing more than one job (the files, the stored answers, the user's own words this session), then ask the user to name and define the thing they mean. Don't propose the canonical term. The user picks it. Their reason for picking it is part of the answer.

### Discuss concrete scenarios

When domain relationships come up, stress-test them with specific scenarios. Invent cases that probe the edges and force the user to be exact about where one concept ends and the next begins. Each scenario is one question. The examiner and sparring-partner personas carry this move well.

### Cross-reference with code

When the user states how something works, check whether the code agrees. Looking it up is your job (dispatch a sub-agent if it's slow). If the code contradicts the user, show both and ask which is right and why: "The code cancels whole orders, but you just said partial cancellation is possible. Which is right?"

## Terms as sparks

A term is settled when the user has named it, defined it, and grounded it. Then it becomes an entry.

- **Ask what it is, assuming the intent.** For example: "What is an Order in this project, and why is it called that rather than a Purchase?" The answer is the user's words, verbatim. It's not trimmed to one sentence.
- **Only this project's terms.** General programming concepts (timeouts, error types, utility patterns) don't get term entries, even if the project uses them heavily. Before asking, check: is this unique to the project, or general?
- **What the term is, not how it's built.** A term entry defines the concept. Implementation belongs in its own `[S]` question.
- **Rejected synonyms are restrictions.** When the user rejects a word for a concept, that is a candidate `[R]` entry that assumes the intent: "Why is 'account' never used for a Customer here?"
- **Type follows the term's home.** Tag the question with the type the concept lives in: `[S]` for stack and architecture, `[P]` for purpose, audience, and packaging, `[A]` for the sensory footprint, `[R]` for what to avoid, `[K]` for knowledge sources.
- **Capture inline.** Propose the entry as soon as the term settles. Don't batch terms for the end. The proposal is that turn's one question, as in sparks-discuss.

If the project has more than one bounded context, work out which one the current topic belongs to and name it in the question ("In billing, what is…"). If it's unclear, ask.

## Decisions as sparks

Matt's bar for an ADR marks the decisions to drill hardest. A decision clears it when all three hold:

1. **Hard to reverse.** Changing your mind later costs something real.
2. **Surprising without context.** A future reader will wonder why it was done this way.
3. **The result of a real trade-off.** There were real alternatives, and one was picked for specific reasons.

When a decision clears all three, ask about it in a way that assumes the intent: "Why does Ordering talk to Billing through domain events rather than direct calls?" Drill the rationale until it rests on nothing unstated. Use the `/why` route if it needs depth. Then propose the entry. Rejected alternatives belong in the answer when the rejection isn't obvious.

What tends to qualify:

- Architectural shape: "The write model is event-sourced; the read model is projected into Postgres."
- Integration patterns between contexts.
- Technology choices with lock-in: database, message bus, auth provider, deployment target.
- Boundary and scope decisions, including the explicit no's. These are often `[R]`.
- Deliberate deviations from the obvious path. These stop the next engineer from "fixing" what was deliberate.
- Constraints that aren't visible in the code: compliance, partner contracts, latency budgets.

A decision that misses the bar can still be a spark if it serves the README's thesis. It just doesn't need the drill.

## Credits

The domain-modeling method (challenge, sharpen, scenarios, cross-reference, inline capture, the glossary rules, and the three-part decision bar) is adapted from Matt Pocock's `domain-modeling` skill. His MIT license is in [`LICENSE`](LICENSE). The interview and the write path are this plugin's `sparks-discuss`. See [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).

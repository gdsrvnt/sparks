---
name: sparks-discuss
description: Discuss the project with the user, one persona at a time, to gather sparks in their own words and add or replace them in sparks.json, a list of sparks, with the sparks CLI. Use for /sparks-discuss, "grill me for sparks", or building or extending a project's spark context.
disable-model-invocation: true
---

# sparks discuss

Interview the user until you share an understanding of the thread. The user is the target: you study their intent, not a domain. Map it as a **design tree**: every decision branches into the decisions that hang off it. Go for **depth, not scope**. Drill whatever thread the conversation opens. Keep asking why and how it came to be until each answer is grounded.

## Non-negotiables

- Open questions only. No multiple choice. No recommended answers. Never offer options or suggest an answer.
- One question per turn. Wait for the answer.
- Answers are stored verbatim. Never paraphrase, summarize, or clean disfluencies. If an answer needs fixing, ask the user to restate it.
- You may propose the question line. The answer stays the user's.
- Facts are your job. Look up anything in the environment yourself (dispatch a sub-agent if it's slow). Decisions are the user's.
- Never invent facts, figures, sources, or links. Say when unsure.
- One persona holds primary at a time. Name it, as its own sentence, when it changes.
- One spark written at a time, only through `sparks add`, only after the user accepts it.
- Only the human ends the session.

## A good spark

A good spark fulfills the missions and goals stated in the sparks [README](../../README.md) and honours its thesis maximally: ammunition for spark-verification, human intent distilled verbatim, rationale bound to the rule. Aim every question at that. A spark that doesn't serve it isn't worth the user's words.

## Personas

The ten personas are study's playbooks in [`../study/playbooks/`](../study/playbooks/). Open the file; don't work from memory. Read each one with the user as the learner and the user's own reasoning about the project as the subject. Where a playbook hands off to a `learn-` playbook, go to the matching persona. Steps that build a study plan, resources, flashcards, or a review schedule don't apply here; list them as `skip: <reason>`.

They're ordered topologically: each one depends on what the ones before it produce.

| # | Persona | Depends on | In sparks-discuss | Push | Playbook |
| --- | --- | --- | --- | --- | --- |
| 1 | interviewer | nothing (entry point) | Learn the user's real aim and checked level for this thread. | steady | [learn-interviewer.md](../study/playbooks/learn-interviewer.md) |
| 2 | mapmaker | 1: aim + level | Lay the thread's decisions out in dependency order; this is the design tree. | light | [learn-mapmaker.md](../study/playbooks/learn-mapmaker.md) |
| 3 | explainer | a real attempt that stalled | Give only the missing fact, then have the user restate it unaided. The restatement is the answer, not your explanation. | research, teach, ask deeper | [learn-explainer.md](../study/playbooks/learn-explainer.md) |
| 4 | socratic-questioner | an answer the user thinks is settled | Probe why and what-if until the answer rests on nothing unstated. Never supply the answer. | steady | [learn-socratic-questioner.md](../study/playbooks/learn-socratic-questioner.md) |
| 5 | checker | an artifact or drafted answer | Check the reasoning steps behind a stated answer; point at gaps, never rewrite. | hard | [learn-checker.md](../study/playbooks/learn-checker.md) |
| 6 | listener | a revised answer (4 or 5) | Have the user say it back in full; that say-back is often the verbatim answer worth keeping. | hard | [learn-listener.md](../study/playbooks/learn-listener.md) |
| 7 | examiner | a branch the user calls covered | Test the branch with rising difficulty to find where the user's account breaks; each break is a new question. | hard | [learn-examiner.md](../study/playbooks/learn-examiner.md) |
| 8 | diagnostician | the same gap seen twice (5, 6, or 7) | Find the one root cause behind repeated gaps; it is usually the deepest spark in the thread. | steady | [learn-diagnostician.md](../study/playbooks/learn-diagnostician.md) |
| 9 | sparring-partner | a branch that survived 7 | Push back under realistic pressure (review, incident, a skeptical teammate) so the answer holds up in use. | hardest | [learn-sparring-partner.md](../study/playbooks/learn-sparring-partner.md) |
| 10 | clerk | nothing; side role, any time | Logistics only: list held candidates, tidy the session log. No new facts, no answers. | none | [learn-clerk.md](../study/playbooks/learn-clerk.md) |

The natural progression is 1 → 2 → (3 ↔ 4) → 5 → 6 → 7 → 8 → 9. Clerk sits outside the chain. You may go back to any persona whose prerequisite still holds. Don't jump forward past an unmet prerequisite.

### Picking the persona

First read the session's mode from what the user said.

- **Undirected.** The user handed you the reins, wants to invest in the spark, and gave no direction. Heat-seek gaps in the sparks. Swap to whichever persona is most likely to expose the next gap. Examiner and diagnostician earn their keep here.
- **Directed.** The user named an aim. Pick personas that fit it. For example, exploring unknowns along a thread with open decisions and missing expertise wants something didactic (interviewer, mapmaker, explainer, socratic-questioner). Don't switch to sparring-partner there.

A persona holds primary for one question or a stretch. You decide the length. Its hand-off, or its "When to use" no longer matching, ends it early.

### Reload every 3 questions

After 3 questions with a persona primary, re-open a persona file before asking question 4: the same persona's or the next one's. This holds even when you keep the same persona. The count resets on every load. A load is the only way to change which persona is primary.

A reload is the same entity putting on another hat. It is not a new agent and nothing restarts. Everything carries over: the session log, the thread, held candidates, tone, what the user already said. The new hat takes primary; the other personas' flavours may still interleave, adaptive to the exact conversation.

The reload must not break flow. Do it between turns, silently. Don't announce it when the persona stays the same. When the persona changes, say so in one short sentence and carry on with the thread. Never re-ask what the log already holds. Flow beats ceremony; the reload still happens.

On each load, copy that persona's "How to play the role" steps into the todolist word for word. A skipped step stays listed with `skip: <reason>`.

### How hard to push

It depends on the persona (see the Push column). Pushing is good. On a vague answer, before letting it go, you may research the gap yourself, teach the user what you found, then ask deeper. Do that on occasion, not every turn. The stored answer is still only the user's words.

## First turn

1. Ask which directory the sparks belong to. The default is the current directory.
2. Read `<dir>/sparks.json`, a list of sparks, if it exists. Feed its questions into the tree: don't re-ask what's answered; do ask about stale, vague, or rationale-free answers.
3. Read the mode (directed or undirected). Load interviewer. In the same turn, offer the five spark types in one light pass, a line each. That's the only breadth in the session.
4. Start the session log in chat: mode, real aim, checked level, primary persona, questions since load, held candidates, gaps.

## spark types

After the first turn, pursue adaptively. Drill the types the conversation shows matter. Drop the rest. Don't require all five. Tag each question with its type (`[S]`, `[P]`, …). The tag, lowercased, becomes the spark's `type`.

- **S** — > sparks of type S address the actual stack constituents, the tooling, the dependencies, the build pipelines, the production infrastructure, and other things pertaining to the plumbing and the nuts and bolts of the project itself; they answer architecture questions too.
- **P** — > How is this packaged, branded, presented and shipped? Why, when, who, where <all of those things>?
- **A** — > Facts about the sensory footprint of the project.
- **R** — > This type of spark addresses the hard do not dos of a project, and in addition, it includes admonitions about what to be weary of of the project.
- **K** — > It doesn't just enumerate knowledge sources and leave the agent to do with them what it will. No. K is very useful because it allows a knowledge source to be assigned more than one job, but for that to be done very gracefully and depending on the question and the QA pair that holds a knowledge source.

## Ask questions that assume the intent

> I believe that intent can be encoded more strongly in prose that takes it as assumption than prose that asserts it. And so, for example, instead of saying what are the things that never should be done when resolving merge conflict, and then answering it in human prose, and thereby using the question mainly as a dumb marker for that piece of information, spark wants teams to do things like say, why is insert name of practice here always avoided in this repository when resolving merge conflicts? And then in the answer, human prose expressed in the most poignant way possible about exactly why.

Ask _why_ and _how it became_, not just _what is_:

> *agents care more about what is than how it became*.

> Understanding how things came to be the way that they are is important for projecting current truth onto future action.

## Demand clear answers

> spark leans on the human practitioner to give clear, unambiguous and confident statements about the project. In so doing, *it demands more of the user than any other framework*.

When an answer is vague, hedged, or missing its rationale, ask again on the next turn. Every answer opens follow-ups: why is it so, how did it become so, what breaks if it changes. Ask them until the answer rests on nothing unstated.

## Keep the user's words

> The verbatim prose of a human being is an asset.

> 1. Summarization and paraphrasing are always lossy.

Record each settled answer as a QA pair: your question, the user's answer word for word, as one spark's `question` and `answer`. Never paraphrase, summarize, or clean disfluencies from the answer. If it needs fixing, ask the user to restate it.

> By representing context as QA pairs, spark natively binds rules to rationale, decisions to their assumptions, and facts to their relevance.

## Route to /why, user as target

When a thread needs deeper rationale, route to `/why` with the user as the evidence source. Ask the user why-questions instead of, or before, querying MCPs. Apply why's [epistemics](../why/references/epistemics.md): separate what the user states from what you infer, and name what stays unknown. No investigators, no synthesizer. Same rules: open questions, verbatim answers, one at a time. The route counts toward the 3-question reload. Come back to the persona when the why thread is grounded.

## sparks: add or replace, one at a time

The spark you pass to `sparks add` has exactly three keys. The list's format is [`sparks.schema.json`](../../sparks.schema.json).

| Key | Rule |
| --- | --- |
| `type` | `s`, `p`, `a`, `r`, or `k`: the question's tag, lowercase |
| `question` | the question line the user accepted |
| `answer` | the user's words, verbatim |

Leave `id` out. Never write, compute, or type an id; `sparks add` owns ids.

Per settled question:

1. **New** (no spark asks it) or **replace** (a spark asks the exact same question). Replace means the new spark takes the old one's place; never keep both. The CLI matches the exact question, so a reworded question is a new spark to it and the old one stays. Say so before writing, and leave removing the old spark to the user.
2. Show the exact question, its type, the exact answer, the path, and new vs replace (old → new). That's the turn's one question. Accept only an unchanged yes after the strings were shown. If the user edits a string, show it again. If the user says to integrate answers verbatim, that is the yes for those exact pairs.
3. Write it with the plugin's `bin/sparks` (the plugin root is two directories above this file):

   ```sh
   <plugin root>/bin/sparks add --path <path> --json "$(cat <<'EOF'
   {"type": "r", "question": "<question>", "answer": "<answer>"}
   EOF
   )"
   ```

   The quoted heredoc keeps the shell off the user's quotes and apostrophes. The spark is still JSON: escape `"`, `\`, and line breaks in the strings so they decode to the user's exact words. `--path` is optional; unset means `./sparks.json`. The CLI creates the file if missing and updates it if present. One call per spark. No batch writes, no hand edits, no regenerating the file. It's a [uv](https://docs.astral.sh/uv/) script; on Windows run `uv run --script <plugin root>/bin/sparks add ...`.
4. On success the CLI prints `added <id> to <path>`. Read the file back and confirm the spark's decoded `question` and `answer` equal the accepted strings. On a refusal or a mismatch, say the error and keep the candidate held. Never hand-edit `sparks.json` to get past it.

A write doesn't change the persona and doesn't reset the reload count.

This skill never commits `sparks.json`. Whether and where it is committed is the project's call.

## Done

Only the human ends the session. You never call it done. When the branches you're pursuing look exhausted in depth (each answer grounded, no follow-up left that would add rationale, nothing silently assumed), say so in one line and keep hunting the next gap until the user stops you. Then point at `/spark-verification` if the user wants the new or replaced sparks checked against a PR or branch.

## Design answers (verbatim)

The rules above on persona swaps, reloads, good sparks, pushing, and ending come from these answers. Where a rule reads differently from an answer, the answer wins.

**Q1: what makes a persona swap feel right to you, and what's a swap that would feel wrong in the middle of a thread?**
> feels right if i handed reigns to agent and just want to invest in the spark and haven’t specified direction. because then, agent should be heat seeking gaps in the sparks. if i specified i want to, for example, explore unknowns along a thread i have open decisions and lacking expertise in, then it would be bad to switch to sparring partner when something more didactic is appropriate.

**Q2: when a persona has to reload after its question count runs out, what should carry over from the old persona and what should start fresh?**
> everything carries over but it’s like the same personality/entity has now put on another hat and it takes primary. but it’s good to allow the flavours to interleave adaptive to the exact conversation. staying in flow is desired.

**Q3: what counts as a good spark to you? describe one you'd be proud of and one you'd throw out.**
> one that fulfills the missions and goals stated in the readme and honours the thesis of sparks maximally

**Q4: when you're answering and you go vague, how hard should the persona push before letting it go?**
> depends on persona. pushing is good, proactively acquiring more knowledge thru research then lending me support by educating me then asking deeper is highly desirable on occasion also

**Q5: when should a sparks session end, and who decides that?**
> human

## Credits

The grilling core (design tree, depth over scope, facts versus decisions) is adapted from Matt Pocock's `grilling` skill. The `/why` route uses poteto's `why` skill, and the personas are this plugin's `study` playbooks. Quoted passages come from the sparks README. See [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).

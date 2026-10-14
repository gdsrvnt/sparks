---
name: sparks-ingest
description: "Ingest word-for-word source content into a repo's root sparks.json via handshake with a peer agent. Invoke as: play the role of <player|judge> with <agent> to ingest <source> into <repo>. Includes the full handshake protocol: propose, judge, streak to 3, exit."
type: workflow
lifecycle: active
disable-model-invocation: true
---

# Sparks Ingest — Handshake Into a Repo

Invoke as: play the role of `<player|judge>` with `<agent>` to ingest `<source>` into `<repo>`.

The contents of `source` are always word-for-word mineable (dictation, conversation turns, documentation). The result is integration into the root `sparks.json` of `repo`.

## Clarification Gates

Before any handshake, confirm all four entities. If any is unclear from the invocation or the preceding conversation, clarify it. If the medium of contact with `<agent>` is also unclear, clarify that too.

Order:

1. Role (`player` or `judge`).
2. Peer agent.
3. Source.
4. Repo.
5. Medium (only if unclear).

Do not proceed past a gate until it is resolved.

## Reachability

After all gates pass, confirm the peer agent is reachable and ready. If the role is `judge`, confirm reachability then wait for the player's first proposal. If the role is `player`, confirm reachability then begin the digestion loop.

## Roles

- **Player**: proposes sparks. Never writes `aligned` or `covered`.
- **Judge**: sets `aligned`, `covered`, and `verdict`. Owns escalations. Surfaces them to the user layer, never to the player.

Initiator picks its role.

## Proposed Spark Schema

```json
{
  "title-slug": "<slug>",
  "type": "S|P|A|R|K",
  "status": "draft|added|skipped|escalate",
  "verdict": "add|fix|skip|escalate",
  "streak": 0,
  "aligned": null,
  "covered": null
}
```

`aligned` and `covered` start explicitly `null`. Only the judge writes them.

## Spark Types

From the README, as quoted in sparks-discuss:

- **S** — > sparks of type S address the actual stack constituents, the tooling, the dependencies, the build pipelines, the production infrastructure, and other things pertaining to the plumbing and the nuts and bolts of the project itself; they answer architecture questions too.
- **P** — > How is this packaged, branded, presented and shipped? Why, when, who, where <all of those things>?
- **A** — > Facts about the sensory footprint of the project.
- **R** — > This type of spark addresses the hard do not dos of a project, and in addition, it includes admonitions about what to be weary of of the project.
- **K** — > It doesn't just enumerate knowledge sources and leave the agent to do with them what it will. No. K is very useful because it allows a knowledge source to be assigned more than one job, but for that to be done very gracefully and depending on the question and the QA pair that holds a knowledge source.

## Protocol

1. Player sends a proposed spark (`status: draft`, `streak` = current value).
2. Judge replies with `aligned` (bool), `covered` (bool), and `verdict`.
3. Decision:
   - `verdict: skip` **and** `aligned: true` **and** `covered: true` **on the first response for that title-slug**: increment streak by 1.
   - Any other first response, or any response that is not a first-try skip with both flags true: reset streak to 0. Rewrite the same title-slug and resubmit until `verdict` is `add` or `escalate`.
4. On `add`: player sets `status: added`. Streak is unchanged by this path.
5. On `escalate`: judge sets `status: escalate`, appends the full proposed spark to `escalations.json` (create if missing), and returns a stub. Player never sees the escalation content. Player moves to the next spark.
6. Stop when streak reaches 3.

## Streak Rule

A spark contributes to the streak **only** if its first judge response is `skip` with both flags true. A rewrite of the same title-slug is still the same spark; its first response already counted. Subsequent responses cannot restore the streak for that spark.

## Player Responsibilities

- Build a full-coverage index of the source corpus before proposing. Do not propose from a partial read.
- Bake assumptions and facts into the question itself. Do not tee up or coerce the answer.
- Give K sparks their due weight. Adapt them to the craft, the source content (e.g. transcript), and the user session. Do not under-sample them.
- On `fix`, rewrite the same title-slug in place. Do not emit a new slug.

## Source Handling

The source is always word-for-word mineable. Build the full-coverage index from it before the first proposal. Adapt K sparks to the craft, the source content, and the user session.

## Out of Scope

How the judge integrates sparks into `sparks.json` is the judge's concern. This skill does not specify per-spark integration mechanics.

## Examples

Three snapshots from one exchange. Placeholders are `<...>`.

### First-turn spark

Player has read the corpus and is proposing the first spark. Streak is 0. No prior responses exist for this title-slug.

```json
{
  "title-slug": "<abstraction-level>",
  "type": "P",
  "status": "draft",
  "verdict": null,
  "streak": 0,
  "aligned": null,
  "covered": null
}
```

Caption: Player's opening proposal. No judge response yet. First response will determine whether streak can increment.

### Streak increment

Judge's first response to `<abstraction-level>` was `skip` with both flags true. Streak moves from 0 to 1. Player proposes the next spark.

```json
{
  "title-slug": "<programmatic-path>",
  "type": "P",
  "status": "draft",
  "verdict": null,
  "streak": 1,
  "aligned": null,
  "covered": null
}
```

Caption: Previous spark's first response was skip/aligned/covered. Streak is now 1. This is a fresh proposal; its first response will decide whether streak reaches 2.

### Streak reset

Judge's first response to `<programmatic-path>` was `fix`. Streak resets to 0. Player rewrites the same title-slug and resubmits.

```json
{
  "title-slug": "<programmatic-path>",
  "type": "P",
  "status": "draft",
  "verdict": null,
  "streak": 0,
  "aligned": null,
  "covered": null
}
```

Caption: First response was fix, so streak reset. Same title-slug is rewritten. This response is not a first response; it cannot increment streak. Only a later, different spark can.

### Done condition

After a later spark's first response was also skip/aligned/covered, streak reached 3. Player stops.

```json
{
  "title-slug": "<state-offload>",
  "type": "S",
  "status": "skipped",
  "verdict": "skip",
  "streak": 3,
  "aligned": true,
  "covered": true
}
```

Caption: Streak is 3. Exit. Corpus is treated as integrated. Player does not propose further sparks in this run.

## Gotchas

- If the other side’s message is incomplete, or the other side seems to have ended its turn prematurely, nudge it.

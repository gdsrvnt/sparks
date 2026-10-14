# Third-party notices

## pstack skills by Lauren Tan (@poteto)

These skills are copied unchanged from the `pstack` plugin in [cursor/plugins](https://github.com/cursor/plugins/tree/118e73b0e196e4d49d5aade7ce6dd8985a621f68/pstack) at commit `118e73b0e196e4d49d5aade7ce6dd8985a621f68`:

- `skills/ketchup/`
- `skills/how/`
- `skills/why/` (modified, see below)
- `skills/bro/`

They're licensed under the MIT License, Copyright (c) 2026 Lauren Tan. The full license text is in [`skills/LICENSE-poteto`](skills/LICENSE-poteto).

`skills/why/` is modified in this plugin: passages that reason about intention were moved word for word out of `skills/why/references/investigator-prompt.md` and the Datadog, Databricks, Linear, Notion and Slack files in `skills/why/references/sources/` into [`docs/uncovering-intention.md`](docs/uncovering-intention.md), and each removal that left a gap now has a one-line pointer to that doc; `skills/why/SKILL.md` Step 3 pastes the relevant sections of the doc into each investigator prompt. Any re-copy of `skills/why/` from upstream must redo this move. The moved text is still poteto's, under the same MIT License, Copyright (c) 2026 Lauren Tan.

These skills are bundled from the same plugin at the same commit. Every file is copied unchanged, and each folder also holds pstack's `LICENSE` (MIT License, Copyright (c) 2026 Lauren Tan) next to its `SKILL.md`:

- `skills/create-verification-skill/`
- `skills/maintain-verification-skill/`

To update them, copy them again from pstack and update this notice.

`skills/spark-verification/` is a separate read-only skill in this plugin and is not an adapter over those two. `skills/sparks-discuss/` routes to the copied `why` skill. poteto's material in the bundled skills and in that route is under the same MIT License, Copyright (c) 2026 Lauren Tan.

## show-me skill by HumanLayer

`skills/show-me/` is copied unchanged from [humanlayer/skills](https://github.com/humanlayer/skills/tree/bba9d13ab34f0a87f1cc33df4dd196372393ddfc/plugins/show-me/skills/show-me) at commit `bba9d13ab34f0a87f1cc33df4dd196372393ddfc`.

It's licensed under the MIT License, Copyright (c) 2026 HumanLayer. The full license text is in [`skills/LICENSE-humanlayer`](skills/LICENSE-humanlayer).

## Skills by Matt Pocock

`skills/sparks-discuss/` adapts its grilling core (design tree, depth over scope, facts versus decisions) from his `grilling` skill in [mattpocock/skills](https://github.com/mattpocock/skills) at commit `95249b0b49782349740fd9b8c6ce32b4e59e497a` ([source](https://github.com/mattpocock/skills/tree/95249b0b49782349740fd9b8c6ce32b4e59e497a/skills/productivity/grilling)).

`skills/sparks-domain/` adapts the `domain-modeling` skill from [mattpocock/skills](https://github.com/mattpocock/skills/tree/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/domain-modeling) at release `v1.3.1`, commit `24fe0ef7737efae15c87225755e9f6f5965e4888`. It keeps the method: challenging terms, sharpening fuzzy language, concrete scenarios, cross-referencing with code, the glossary rules, and the three-part bar for recording a decision. It runs inside the `sparks-discuss` interview and writes sparks through `bin/sparks add` instead of `GLOSSARY.md` and ADR files. The skill's `GLOSSARY-FORMAT.md`, `ADR-FORMAT.md`, and `agents/openai.yaml` are not copied. The folder also holds his `LICENSE` next to its `SKILL.md`.

`skills/sparks-postcall/` adapts the `to-spec` skill from [mattpocock/skills](https://github.com/mattpocock/skills/tree/49dd158d1076134a641b33efb035946536778336/skills/engineering/to-spec) at commit `49dd158d1076134a641b33efb035946536778336`. It keeps the rule to synthesize instead of interviewing and the core of the spec template: Problem Statement, Solution, User Stories, Implementation Decisions, Testing Decisions, and Out of Scope. It adds Source, Relay divergences, Requirements, and Open Questions, and drops Further Notes, the user-story example, and the prototype-snippet exception. It drops the step that checks test seams with the user and the publish to an issue tracker with the `ready-for-agent` label. It reads a call transcript instead of the live conversation, grounds requirements in verbatim quotes, and adds verification, gap implementation, review, and merge steps. The skill's `agents/` folder is not copied. The folder also holds his `LICENSE` next to its `SKILL.md`.

`skills/implement-spec/` adapts the `implement-spec` skill from [mattpocock/skills](https://github.com/mattpocock/skills/tree/49dd158d1076134a641b33efb035946536778336/skills/engineering/implement-spec) at commit `49dd158d1076134a641b33efb035946536778336`. It keeps the integration branch, the task-graph frontier, context pointers, and the implementer, merger, and code-review steps. The TDD and review steps name workflows rather than assuming Claude's Skill tool is installed in every harness. It drops hedges and generic issue-tracker branches, including `/setup-matt-pocock-skills`. Kept sentences add at most two words. It adds a herdr runtime (16 lines of command snippets, two at a time) and workspace cleanup after a big job. The skill's `agents/` folder is not copied. The folder holds his `LICENSE` next to its `SKILL.md`. `herdr-operations` follows this file as its implementation playbook.

All four are licensed under the MIT License, Copyright (c) 2026 Matt Pocock. The full license text is in [`skills/LICENSE-mattpocock`](skills/LICENSE-mattpocock).

## BMad Method

[`skills/LICENSE-bmad`](skills/LICENSE-bmad) is the MIT license from [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) at commit `8f0d50e1817fdd8fcf05a20c524218222d13cd8d`, Copyright (c) 2025 BMad Code, LLC. `CONTRIBUTORS.md` and `TRADEMARK.md` are not copied. No BMad skill or workflow is copied. The license is here so later spec work can credit BMad. Brian Madison ([@bmadcode](https://github.com/bmadcode)) created BMad Method.

## subagent skill by Mario Zechner (@badlogic)

`docs/house/community-skills/subagent/SKILL.md` is copied unchanged from Mario Zechner's [gist](https://gist.github.com/badlogic/d36e325248b68414e1c6528c6ed6b525/3d7d74a92bef0ff41827df1db3a0f49e0f5b1e4b) at revision `3d7d74a92bef0ff41827df1db3a0f49e0f5b1e4b`. It is a community skill in the house library, kept with its source for reference. It is not a plugin skill. The gist states no license, so this copy carries no license grant from this project. [`NOTICE`](docs/house/community-skills/subagent/NOTICE) next to it records the source.

## XXH64 from xxHash by Yann Collet

`spark_hash.py` is a pure-Python port of the XXH64 algorithm from [xxHash](https://github.com/Cyan4973/xxHash/tree/680bf463fa1ca0461b9a7c2dab7556e1f54cf4cf) (license checked at commit `680bf463fa1ca0461b9a7c2dab7556e1f54cf4cf`). No C code is copied.

The xxHash library is licensed under the BSD 2-Clause License, Copyright (c) 2012-2021 Yann Collet. The full license text is in [`LICENSE-xxhash`](LICENSE-xxhash), next to `spark_hash.py`.

# Spec: implement-spec as the herdr implementation playbook

Synthesized from issue #61 and the sparks tree, using Matt Pocock's to-spec skill (read from mattpocock/skills at commit `49dd158`, not installed). Published on sub-issue #84. No interview. Standard headings below are stable so a later digest-specs skill can find them. Do not rename them.

The build that follows this spec is [sparks #86](https://github.com/gdsrvnt/sparks/pull/86). This draft is the spec record, not a second implementation.

## Problem Statement

sparks can hand coding work to herdr, but it has no implementation playbook for turning a spec and its tickets into code. Matt Pocock's implement-spec skill is the right substrate, and it hedges for many working styles and a generic issue tracker. That generality is not needed here. The herdr skill also cannot enumerate active tabs per workspace from the shared snapshot without a new dependency, and the README credits are still a footnote.

## Solution

Bundle an adapted implement-spec skill as the implementation playbook that herdr-operations follows. Subtract the hedges. Keep Matt's license next to the skill. Show multi-model herdr runs and filial tab ownership in at most sixteen lines of command snippets, two lines at a time. After a big job, prune only the workspaces that job created. Extend the existing herdr snapshot, do not replace it, with a read-only enumeration of active tabs per workspace. Use stdlib SQLite and arithmetic, and record that dependency strategy as a root type S spark. Upgrade the README credits into a hall of fame, including Lauren Tan's playbook convention, Matt's human-in-the-loop paradigm, and BMad Method with its creator named. Leave plaques and badge photos for a later pass. Publish this spec on a draft pull request against a sub-issue so an older digest-specs skill and BMad extensions can be attached later without rewriting these headings.

## User Stories

1. As a sparks maintainer, I want implement-spec bundled with Matt Pocock's license next to its SKILL.md, so that the adaptation stays attributable.
2. As a herdr operator, I want herdr-operations to point at that file as its implementation playbook, so that spec implementation has one procedure.
3. As a herdr operator, I want the playbook to drop generic issue-tracker hedges, so that sparks always closes work through GitHub.
4. As a herdr operator, I want kept sentences to add at most two words, so that the adaptation stays close to the substrate.
5. As a herdr operator, I want up to sixteen lines of command snippets, two at a time, so that the runtime shows how several models run in herdr.
6. As a parent agent, I want those snippets to show that I own the tabs I create, so that filial ownership is explicit.
7. As a child agent, I want the prompt to say I own only my ticket, so that I do not take the parent's tabs.
8. As a herdr operator, I want Anthropic models in Claude Code and xAI and OpenAI models in pi, so that harness choice follows the model's maker.
9. As a herdr operator, I want the playbook to say only those two harnesses are used, so that other harnesses are not introduced.
10. As a herdr operator, I want cleanup instructions after a big job, so that job workspaces do not linger.
11. As a herdr operator, I want a workspace closed only when I created it and it holds no user tabs, so that the user's tabs survive.
12. As a herdr operator, I want sparks herdr tabs to list active tabs per workspace from the shared snapshot, so that I can see what a job still holds.
13. As a herdr operator, I want that command not to call herdr and not to write the database, so that a read cannot disturb the snapshot.
14. As a sparks maintainer, I want the counts to come from simple SQL and the active count from arithmetic, so that the rule is inspectable.
15. As a sparks maintainer, I want a tab treated as active when its status is not exactly done, so that unknown, working, blocked, idle, and null still count.
16. As a sparks maintainer, I want this path to use stdlib sqlite3 only, so that sparks stays dependency-free for herdr state.
17. As a sparks maintainer, I want jsonschema to stay on sparks add and not load on the tabs path, so that the dependency strategy is real.
18. As a sparks maintainer, I want that strategy recorded as a root type S spark, so that agents can read it from sparks.json.
19. As a reader of the README, I want Lauren Tan credited on her existing line for the playbook convention, so that the convention's author is named where she already is.
20. As a reader of the README, I want Matt Pocock credited for driving ideation through active human deliberation, called "Human IS the loop", and for pushing AFK work to just after the human session, so that the paradigm is named.
21. As a reader of the README, I want the same credit to note that sparks diverges by leveraging Grok Bot's initiative, so that the two motions can happen orthogonally.
22. As a reader of the README, I want the credits section to read as a hall of fame, not a footnote, so that these inspirations are honored in the text.
23. As a reader of the README, I want BMad Method and its creator, Brian Madison, credited by name, so that the license we hold is attached to a person.
24. As a reader of the README, I want Dex credited for show-me, so that the polish contribution is named before any badge art exists.
25. As a later editor, I want BMad's license file in the repo, so that credit is not a claim without the license text.
26. As Goddy, I want this spec on a draft pull request against a sub-issue of #61, so that I can attach an older digest-specs skill to that issue.
27. As Goddy, I want the standard spec headings left intact, so that digest-specs can find them.
28. As a later author, I want room to extend to-spec toward specs that digest-specs likes, so that this spec does not freeze the template.
29. As a later author, I want room to bake BMad planning into that extension, so that BMad goodness is not forced into this pass.
30. As sol, I want plaques, public profile photos, Pen Badge stitching, and Dex's Onyx Badge left undone, so that photo generation is a separate review task.
31. As a reviewer, I want the herdr skill to start from the latest herdr-operations text on any branch, so that older wording is not revived.
32. As a reviewer, I want sparks herdr snapshot left in place, so that this work extends the snapshot instead of replacing it.

## Implementation Decisions

- The playbook is an adapted skill, not a rewritten one. Hedges and generic issue-tracker branches come out. Kept sentences gain at most two words. New runtime snippets and cleanup instructions are additions the issue allowed, not silent rewrites.
- Issue tracking for this playbook is GitHub. There is no setup step for another tracker.
- Subagents in the playbook are herdr agents. The parent owns tabs it creates. A child owns only the ticket named in its prompt. One agent per tab. Names say the job.
- Model variety is shown by harness, not by installing new harnesses. Claude Code for Anthropic models. pi for xAI and OpenAI models. Effort flags follow the herdr-operations rules.
- Snippets are commands, two lines at a time, sixteen lines in total. They are the runtime refit. They do not replace the task-graph steps.
- Cleanup closes tabs and panes the job opened. It closes a workspace only when that job created the workspace and no user tab remains. It then refreshes the snapshot and re-reads active tabs.
- Herdr state enumeration is a new read action on the existing sparks herdr command. It does not add a snapshot format and does not call herdr.
- SQL counts stored tabs and done tabs per workspace, including a workspace with no tab rows and tab rows whose workspace row is missing. Active is stored minus done, computed in process, then checked against the listed non-done tabs.
- A tab is active when agent_status is not exactly done. Null counts as active.
- The read opens an existing snapshot read-only and immutable. It does not create a file, a parent directory, or a sidecar. Pending journal data is an error. A snapshot that changes during the read is an error.
- The dependency strategy is: stdlib sqlite3 only; no SQL driver, ORM, or query package; jsonschema is imported only when add runs. That strategy is also a root type S spark.
- README credits become a hall of fame. Lauren Tan's existing line gains the playbook-convention credit at its end. Matt Pocock's credit gains the HITL paradigm and the sparks divergence. Brian Madison is credited as BMad Method's creator, using the public name on the BMad about page, because the BMAD-METHOD README does not print it. Dex is credited in text for show-me.
- BMad's MIT license is copied so the credit is backed by the license text. No BMad skill or workflow is copied.
- Plaques, profile photos, Pen Badge stitching, and the Onyx Badge are not part of this implementation.
- The herdr-operations text starts from the latest copy on any branch, then gains the playbook pointer, filial ownership, tabs enumeration, and workspace pruning.
- This spec's headings stay as in the to-spec template so a later digest skill can key off them. BMad planning artifacts are not baked into those headings in this pass.

## Testing Decisions

A good test checks external behavior, not the shape of private helpers. The modules under test are the sparks herdr tabs command, the packaged playbook text, and the root spark that records the dependency strategy.

Prior art is the existing herdr snapshot suite: a fake herdr on PATH, an isolated database, and assertions that a read does not call herdr or change the file. Follow that. Also assert the playbook's snippet fences are eight fences of two lines, that the herdr skill points at the playbook, that the license file beside the skill matches Matt's license, and that the tabs path does not import jsonschema.

The seam is that command's stdout and the packaged skill files. Internal SQL text is not the seam.

## Out of Scope

- Replacing sparks herdr snapshot.
- The read-only query command already proposed on an open pull request. This spec does not reimplement it.
- Installing or vendoring Matt's to-spec skill as a new sparks skill in this pass. sparks-postcall already adapts an older to-spec.
- Goddy's digest-specs skill, and any rewrite of this template to suit it.
- Baking BMad workflows, agents, or planning steps into the playbook or into to-spec.
- Plaques, photo generation, Pen Badge stitching, and Dex's Onyx Badge.
- Closing #61. Review and the deferred badge work remain.

## Further Notes

Extension points, left empty on purpose:

- digest-specs: attach Goddy's older skill to the sub-issue of this spec. It should keep the headings Problem Statement, Solution, User Stories, Implementation Decisions, Testing Decisions, Out of Scope, and Further Notes. A later change may add the fields that skill likes. Do not rename these headings in that change; add beside them.
- BMad: a later extension of to-spec may bake in BMad planning. The license file is the attribution for that work. Do not copy BMad skills until that extension is specified. Brian Madison is the creator to credit.
- Badges: sol 6.1 adds plaques and stitches public profile photos. Pen Badge acknowledges intellectual contribution. Onyx Badge acknowledges Dex's polish on show-me. Do not invent photos.

Open question for Goddy: the test seam above is the tabs stdout contract plus the packaged skill files. Say if you want a different seam before digest-specs locks this spec.

BMad's license on this branch is `skills/LICENSE-bmad`, copied from bmad-code-org/BMAD-METHOD at commit `8f0d50e`. It is here so this draft can credit BMad before any BMad workflow is copied.

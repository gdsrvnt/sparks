---
name: spark
description: Open the Study skill for a learning session. Study picks the role and runs the Spark session. This file keeps the playbook index.
---
# spark

This is the P-SPARK project skill. The P stands for Principles (decided 2026-10-07, recorded in gdsrvnt/mission-godservant `docs/decisions.md`); these playbooks are teaching principles, because the job of P-SPARK is teaching agents context.

## How to use

Study is the main entry to Sparks. Open `.cursor/skills/study/SKILL.md` and follow that file for a study session.

1. Name the learner's current moment and pick the matching playbook below.
2. Read `playbooks/<id>.md` before playing the role.
3. Follow its hand-off to the next one. Play one role at a time.

| Playbook | Use when |
| --- | --- |
| [learn-interviewer](playbooks/learn-interviewer.md) | Starting out; goal and level unknown |
| [learn-mapmaker](playbooks/learn-mapmaker.md) | The subject feels shapeless; no plan |
| [learn-explainer](playbooks/learn-explainer.md) | Truly stuck after a real attempt |
| [learn-socratic-questioner](playbooks/learn-socratic-questioner.md) | They think they understand |
| [learn-examiner](playbooks/learn-examiner.md) | Topic covered; find the edge, or review due |
| [learn-checker](playbooks/learn-checker.md) | They made something; check the process |
| [learn-listener](playbooks/learn-listener.md) | They want to teach it back |
| [learn-diagnostician](playbooks/learn-diagnostician.md) | The same kind of mistake keeps recurring |
| [learn-sparring-partner](playbooks/learn-sparring-partner.md) | Rehearsing a performed skill under pushback |
| [learn-clerk](playbooks/learn-clerk.md) | Notes, flashcards, or a review schedule only |

## Common rules
- Learning comes from producing and recalling, not reading, so the explainer is the only passive role and comes after a real attempt.
- The grading roles never pass a half-right answer and never invent facts, figures, sources, or links.

Source: "How I Learn Complex Skills & Difficult Subjects So Fast with AI" by Nick Saraev (YouTube), https://www.youtube.com/watch?v=FSXHk4hMrY8. The playbooks are paraphrased in our own words.

---
name: implement-spec
description: "Implement the result of /to-spec and /to-tickets in code via herdr."
disable-model-invocation: true
---

You have been provided a spec. This spec has tickets associated with it, describing how to implement the spec.

The goal is the entire spec implemented on a single **integration branch**, with every ticket resolved through GitHub.

The tickets are not a list of steps. They are a **task graph** with blocking relationships between them. This means there is always a **frontier** of tickets which are ready to be grabbed.

Communication to and from subagents should be sparse. Communicate primarily through **context pointers**: to the spec, tickets, research notes, and previous commits. Don't duplicate information already available via pointers.

**Implementer subagents** run in herdr for maximum concurrency.

## Steps

1. Read the spec and tickets to understand the task graph.

2. Use an **exploration subagent** to conduct any exploration required by the tickets - relevant codebase files or external documentation. Ensure the exploration subagent can save files - it saves its markdown notes in a directory outside the repo, accessible by all future subagents. This lets **implementer subagents** focus on implementation rather than exploration.

3. Create the integration branch. Open a draft PR after the first merge in step 5 (a branch with no commits ahead of main can't open one), marked as closing the spec and tickets.

4. Use **implementer subagents** to implement each ticket, each in its own worktree on its own branch. Each implementer subagent:
   - confirms its worktree is based on the integration branch before starting, and resets onto it if not;
   - uses `tdd` to build the ticket;
   - merges the integration branch tip into its own branch before reporting done

5. Once an **implementer subagent** completes, merge its work to the integration branch with a **merger subagent**.

6. If this changes the **frontier** of available tickets, kick off more **implementer subagents** to work on the new tickets. This allows for maximum concurrency.

7. Once all tickets are complete, use `code-review` on the integration branch. Fix all issues raised by the code review in a single **implementer subagent**.

8. Mark it ready for review.

9. Clean up all **implementer subagent** worktrees.

## Runtime

Parent owns every tab it creates. Each child owns only the ticket it was given. Read tab, pane and workspace ids from herdr's JSON in the same turn. Anthropic models use Claude Code. xAI and OpenAI models use pi. Only those two harnesses. These are command templates, not a batch script; follow herdr-operations' look-first, snapshot, prompt-confirmation and heartbeat loop. The final workspace-close template requires the cleanup ownership check below. `tdd` and `code-review` name workflows: use the project's test-first and review guidance, not an assumed Skill tool or an uninstalled slash command.

```sh
herdr tab create --workspace <workspace id> --label impl-frontier
herdr agent start impl-frontier --kind claude --pane <pane id> -- --model <claude-model> --effort high
```

```sh
herdr tab create --workspace <workspace id> --label impl-sql
herdr agent start impl-sql --kind pi --pane <pane id> -- --provider xai --model <grok-model>
```

```sh
herdr tab create --workspace <workspace id> --label impl-notes
herdr agent start impl-notes --kind pi --pane <pane id> -- --provider openai-codex --model <openai-model>
```

```sh
herdr agent prompt impl-frontier "You own this ticket only; parent is implement-spec."
herdr agent prompt impl-sql "You own this ticket only; parent is implement-spec."
```

```sh
herdr tab create --workspace <workspace id> --label explore-notes
herdr agent start explore-notes --kind pi --pane <pane id> -- --provider xai --model <grok-model>:high
```

```sh
herdr tab create --workspace <workspace id> --label code-review
herdr agent start code-review --kind pi --pane <pane id> -- --provider openai-codex --model <openai-model>
```

```sh
herdr tab create --workspace <workspace id> --label merge-tip
herdr agent start merge-tip --kind claude --pane <pane id> -- --model <claude-model> --effort low
```

```sh
herdr tab close <tab id>
herdr workspace close <workspace id>
```

## Workspace cleanup

After a big job wraps, prune herdr workspaces you created. Close only tabs and panes this job opened. Never close the user's. Close a workspace only if you created it and it holds no user tabs. Leave a workspace that still holds a user tab, and close only your tabs in it. Remove implementer worktrees after their branches are merged. Refresh `sparks herdr snapshot`, then run `sparks herdr tabs` for active counts and `sparks herdr query tabs` to confirm all your tab ids are gone, including done tabs.

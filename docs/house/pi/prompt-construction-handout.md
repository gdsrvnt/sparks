# Pi extension developer handout: rules are not the harness

**Lecture digest · Pi 1.0.4.** Pi is a prompt compiler plus a request pipeline. The [matrix](prompt-construction-matrix.md) owns exact defaults, provenance, and precedence; this page covers intervention and review.

## Three layers, three different powers

```text
Files / CLI / SDK / registered tools
                 |
        normalized prompt options
                 |
       before_agent_start hooks
                 |
          section compiler
                 |
   structured transcript + tool declarations
                 |
 context -> context_with_system transforms
                 |
 hidden-tool / forced-prompt request projection
                 |
  provider serialization -> payload/header hooks -> service
```

1. **Instructions:** `rules` advises the model; it is not an enforcement engine. `customPrompt` changes one compiler branch, not the downstream pipeline.
2. **Composition:** append guidelines for conventions; add a uniquely named section for domain context. Section replacement owns the complete contents. Handler order resolves extension mutations.
3. **Request control:** forced text retains conversation/tools but can diverge from structured session records. Payload hooks and custom providers can change requests further.

## Build the smallest useful extension

```ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.on("before_agent_start", (event) => {
    event.systemPromptOptions.promptGuidelines.push(
      "State which tests you ran before reporting completion."
    );
    event.systemPromptOptions.sections.team_context =
      "This repository maintains backward-compatible public APIs.";
  });
}
```

The guideline needs default rules; the named section survives a custom prompt. Force replacement only when deliberately owning the whole textual prompt, and disclose it. Packages distribute executable hooks, not declarative “force prompt” settings.

## Extension power: capability and review checklist

| Surface | Useful capability / unexpected consequence |
|---|---|
| `input`, message injection | Transform or consume user input; send messages and trigger work |
| `context`, `context_with_system` | Filter request history; the latter owns system/tool state too |
| `before_provider_request`, `before_provider_headers` | Replace outgoing payload; mutate/delete headers |
| `registerTool`, `prepareLoadout`, tool hooks, `user_bash` | Override built-ins, hide declarations, alter/block arguments, replace results, redirect shell execution |
| `message_end`, compaction/tree hooks, continuation boundaries | Replace finalized messages/summaries, cancel transitions, add context and extra model turns |
| Provider/virtual-model registration, model/thinking controls, MCP registration | Change endpoints, authentication, request routing, tools, cost, and data destination |
| Resource/trust hooks, ordinary Node.js code | Add resources, decide project trust; access files, credentials, processes, and network with Pi's permissions |

Pin/review packages **and dependencies**. Inspect hooks, reachable tools, physical model destinations, and redacted requests. Test competing hooks, resume/reload, and noninteractive modes. Transcript review and annotation hints are not isolation: sandbox the **whole process** for a real boundary.

## Where Pi documents this

Upstream `main` links may differ from this inspected release:

- [Extensions: Events and concurrency](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/extensions.md#events) explicitly documents returned `systemPrompt` and `forceSystemPrompt`; also see Tools and Context/session changes.
- [Exact hook contracts](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/src/core/extensions/types.ts), [prompt-customizer example](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/examples/extensions/prompt-customizer.ts), and [built-in tool override example](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/examples/extensions/tool-override.ts).
- [Custom providers](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/custom-provider.md), [virtual models](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/virtual-models.md), and [security](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/security.md).

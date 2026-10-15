/**
 * Standalone persona prototype for pi 1.2.0 (not a sandbox for other extensions).
 *
 * pi --provider openai-codex --model gpt-6.1-sol \
 *   -e library/pi-extensions/persona-prototype.ts --persona-trace -p 'Inspect TASK.md'
 * With --no-extensions, also pass -e builtin:codemode (codemode ships with pi).
 * Optional: --persona-code-model gpt-6-sol --persona-base-model gpt-6.1-sol
 * Defaults differ on the wire: base=gpt-6.1-sol, code=gpt-6-sol (Codex only).
 * --persona-auto-check runs the deterministic prerequisite without model cooperation.
 *
 * Native skills are instructions, not executable capabilities. This example owns
 * the advertised catalog, guards explicit skill commands and file access, preloads
 * a mandatory skill, and gates its read capability on a deterministic check tool.
 * It cannot prove that an LLM followed a skill or force a refusing LLM to call it.
 * Only one corrective continuation is attempted; inspect the final audit entry.
 * Start a fresh session with reviewed extensions, --no-mcp and --no-context-files
 * for a clean persona. Existing history/user messages can already contain skills.
 */
import { mkdtempSync, readFileSync, realpathSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { isAbsolute, join, relative, resolve } from "node:path";
import { Type } from "typebox";
import { formatSkillsForPrompt, type ExtensionAPI } from "@earendil-works/pi-coding-agent";

// Markdown pasted directly into a template literal. Escape literal backticks and
// ${...} when pasting other Markdown; ordinary newlines need no escaping.
const PERSONA = `# Sparks persona prototype

## Role
You are a careful, read-only investigator. Never claim an unrun test passed.
Read relevant sparks.json files before working; sparks override conflicting skills.
Report conflicts to the caller. Do not silently rewrite the user's intent.

## Workflow
Use codemode for all tools. First run tools.persona_check({}). Then inspect files
with tools.persona_read({path: "..."}). Only sparks-persona-check is an allowed skill.
Follow its instructions before answering. Distinguish evidence from inference.
Do not use classifier/image models through codemode's models global.
`;

const SKILL_NAME = "sparks-persona-check";
const SKILL = `---
name: sparks-persona-check
description: Required evidence check for this read-only persona, on every task.
---
# Evidence check
1. Run the deterministic persona_check tool before file inspection.
2. Read relevant sparks.json files and report any conflict with these instructions.
3. In the final answer, distinguish observed results from untested assumptions.
A tool receipt proves execution of the check, not semantic compliance with this text.
`;

export default function personaPrototype(pi: ExtensionAPI) {
  pi.registerFlag("persona-trace", { description: "Log persona decisions to stderr", type: "boolean", default: false });
  pi.registerFlag("persona-base-model", { description: "OpenAI Codex model for ordinary requests", type: "string", default: "gpt-6.1-sol" });
  pi.registerFlag("persona-code-model", { description: "OpenAI Codex model for codemode follow-ups", type: "string", default: "gpt-6-sol" });
  pi.registerFlag("persona-auto-check", { description: "Execute the deterministic prerequisite before each run", type: "boolean", default: false });
  const trace = (event: string, data: unknown) => {
    if (pi.getFlag("persona-trace")) console.error(`[persona:${event}] ${JSON.stringify(data)}`);
  };

  // No factory I/O: --help / --list-models load extensions without a session.
  // /new, /resume and fork tear down this runtime and create another one.
  let skillDir: string | undefined;
  let skillPath: string | undefined;
  let checked = false;
  let nudged = false;
  let misconfigured = false;
  const ensureSkill = () => {
    if (!skillDir) skillDir = mkdtempSync(join(tmpdir(), "sparks-persona-"));
    if (!skillPath) {
      const path = join(skillDir, "SKILL.md");
      writeFileSync(path, SKILL, { mode: 0o600 });
      skillPath = realpathSync(path);
      trace("skill-created", { path: skillPath });
    }
    return skillPath;
  };
  pi.on("resources_discover", () => ({ skillPaths: [ensureSkill()] })); // Additive, NOT an allowlist.
  pi.on("session_shutdown", (event) => {
    if (skillDir) rmSync(skillDir, { recursive: true, force: true });
    trace("skill-removed", { reason: event.reason, path: skillPath });
    skillDir = skillPath = undefined;
  });
  // The tool and the opt-in model-independent path execute the same prerequisite.
  const runCheck = (source: "tool" | "extension") => {
    checked = true;
    const receipt = { skill: SKILL_NAME, ran: true, source };
    pi.appendEntry("persona-check", receipt);
    trace("check", receipt);
    return receipt;
  };

  pi.registerVirtualModel({
    provider: "sparks",
    id: "persona-prototype",
    name: "Sparks persona prototype",
    thinkingLevels: ["minimal", "low"],
    route(request, ctx) {
      // Route the next inference, not JavaScript execution. A mixed batch uses
      // the code route if ANY top-level codemode result follows the last assistant.
      // User requests and direct calls (e.g. compaction) always use the base route.
      let lastAssistant = -1;
      for (let i = request.messages.length - 1; i >= 0; i--) {
        if (request.messages[i].role === "assistant") { lastAssistant = i; break; }
      }
      const afterCode = (request.reason === "continuation" || request.reason === "retry") &&
        lastAssistant >= 0 && request.messages.slice(lastAssistant + 1).some(
          (message) => message.role === "toolResult" && message.toolName === "codemode",
        );
      const id = String(pi.getFlag(afterCode ? "persona-code-model" : "persona-base-model"));
      // Deliberately never select xai, including when a user changes these flags.
      const model = ctx.modelRegistry.find("openai-codex", id);
      if (!model) throw new Error(`Unknown openai-codex model: ${id}`);
      const thinkingLevel = afterCode ? "low" as const : "minimal" as const;
      trace("route", { reason: request.reason, role: afterCode ? "code" : "base", model: model.id, thinkingLevel });
      return { model, thinkingLevel };
    },
  });

  const activate = () => {
    // Built-ins are direct-exposure tools: inactive means NOT callable in scripts.
    // Our two codemode-exposure tools remain callable without being declared.
    pi.setActiveTools(["codemode"]);
    trace("active", pi.getActiveTools());
    return pi.getActiveTools().includes("codemode");
  };
  pi.on("session_start", () => { activate(); });
  pi.on("before_agent_start", async (event, ctx) => {
    checked = false;
    nudged = false;
    misconfigured = false;
    // Apply policy before validating the loadout. Hook exceptions alone do NOT
    // stop pi: fail closed with an explicit abort and a defensive refusal prompt.
    event.systemPromptOptions.customPrompt = PERSONA;
    event.systemPromptOptions.appendSystemPrompt = "";
    event.systemPromptOptions.skills = event.systemPromptOptions.skills.filter(
      (skill) => skill.name === SKILL_NAME && skill.filePath === skillPath,
    );
    // Pi auto-renders skills only when native read/bash is active. We use a
    // restricted custom reader, so explicitly render the filtered advertisement.
    event.systemPromptOptions.sections.skills =
      "Use codemode tools.persona_read to load skills.\n" +
      formatSkillsForPrompt(event.systemPromptOptions.skills, "indirect");
    trace("skills", event.systemPromptOptions.skills.map((skill) => skill.name));
    try {
      const router = ctx.modelRegistry.find("sparks", "persona-prototype");
      if (!router || !await pi.setModel(router)) throw new Error("Cannot select persona router");
      if (!activate()) throw new Error("Enable pi's built-in codemode extension (-e builtin:codemode when using -ne)");
      if (!skillPath) throw new Error("Persona skill discovery did not complete");
    } catch (error) {
      misconfigured = true;
      pi.setActiveTools([]);
      console.error(`[persona:misconfigured] ${String(error)}`);
      ctx.abort(); // pi 1.2.0 honors startup aborts before its first request.
      return { systemPrompt: "Persona misconfigured. Refuse all work; do not call tools." };
    }
    if (pi.getFlag("persona-auto-check")) runCheck("extension");
    // Guaranteed delivery, not obedience. Avoid accumulating full copies on
    // repeated prompts; a fork that excludes the entry gets its own first copy.
    const delivered = ctx.sessionManager.getBranch().some(
      (entry) => entry.type === "custom_message" && entry.customType === "persona-required-skill",
    );
    if (event.messageType === "user" && !delivered) {
      return { message: { customType: "persona-required-skill", content: `Required skill:\n${SKILL}`, display: false } };
    }
  });

  pi.on("input", (event) => {
    const command = event.text.match(/^\s*\/skill:([^\s]+)/);
    if (command && command[1] !== SKILL_NAME) {
      trace("skill-command-blocked", command[1]);
      return { action: "handled" }; // Before native skill-command expansion.
    }
  });
  pi.on("user_bash", () => ({ result: { output: "Persona blocks user shell escapes", exitCode: 1, cancelled: false, truncated: false } }));
  pi.on("tool_call", (event) => {
    trace("tool", { name: event.toolName, nested: !!event.parentToolCallId });
    if (misconfigured) return { block: true, reason: "Persona misconfigured" };
    if (!["codemode", "persona_check", "persona_read"].includes(event.toolName)) {
      return { block: true, reason: "Tool is outside the persona allowlist" };
    }
    if (event.toolName === "persona_read" && !checked) {
      return { block: true, reason: "Run persona_check before reading files" };
    }
  });
  pi.on("tool_result", (event) => {
    trace("result", { name: event.toolName, nested: !!event.parentToolCallId, isError: event.isError });
  });

  pi.registerTool({
    name: "persona_check", label: "Persona evidence check", exposure: "codemode",
    description: "Run the mandatory deterministic check; returns the allowed skill and a receipt. Call before persona_read.",
    parameters: Type.Object({}),
    async execute() {
      const receipt = runCheck("tool");
      return { content: [{ type: "text", text: `${JSON.stringify(receipt)}\n${SKILL}` }], details: receipt };
    },
  });
  pi.registerTool({
    name: "persona_read", label: "Persona bounded reader", exposure: "codemode",
    description: "Read one UTF-8 file within cwd (max 64 KiB), or this persona's allowed SKILL.md. Other SKILL.md files are denied.",
    parameters: Type.Object({ path: Type.String() }),
    async execute(_id, args, _signal, _update, ctx) {
      // Repeat the gate inside execution, rather than relying only on a hook.
      if (!checked) throw new Error("Run persona_check first");
      const root = realpathSync(ctx.cwd);
      const path = realpathSync(resolve(root, args.path));
      const rel = relative(root, path);
      if (path !== skillPath && (rel === ".." || rel.startsWith("../") || rel.startsWith("..\\") || isAbsolute(rel) || /(^|[/\\])SKILL\.md$/i.test(path))) {
        throw new Error("Path is outside the persona file/skill policy");
      }
      const stat = statSync(path);
      if (!stat.isFile() || stat.size > 65536) throw new Error("Only regular UTF-8 files up to 64 KiB are allowed");
      return { content: [{ type: "text", text: readFileSync(path, "utf8") }], details: { path } };
    },
  });

  pi.on("agent_before_settle", (event) => {
    if (!misconfigured && !checked && !nudged && event.outcome === "completed") {
      nudged = true; // Bounded: never manufacture an infinite model loop.
      return {
        continue: true,
        entries: [{ type: "custom_message", customType: "persona-check-required", content: "Before final settlement, call codemode: text(await tools.persona_check({})).", display: false }],
      };
    }
  });
  pi.on("agent_settled", () => {
    const audit = { checked, nudged, misconfigured, semanticCompliance: "not mechanically provable" };
    pi.appendEntry("persona-audit", audit);
    trace("audit", audit);
  });
}

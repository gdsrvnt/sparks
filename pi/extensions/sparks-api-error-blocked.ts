// sparks-api-error-blocked: tell herdr when a pi run ends in a model API error.
//
// Without this, an API error drops pi to idle, which herdr shows the same as
// a finished turn. When a run settles (no automatic retry, compaction, or
// queued continuation will follow) and its last assistant message stopped
// with stopReason "error", this extension:
//
//   1. emits "herdr:blocked" with { active: true, label: "sparks:api-error: <error>" }
//      on pi's extension event bus. herdr's own pi extension
//      (herdr-agent-state.ts, managed by herdr) listens for it and reports
//      the pane as blocked with that message over HERDR_SOCKET_PATH.
//   2. sets the herdr pane token sparks_api_error to the error text with
//      pane.report_metadata, the same newline-delimited JSON socket request
//      shape herdr's extension uses. herdr agent get shows pane tokens but
//      not the blocked message, so this token is how sparks agent spawn tells
//      an API error from an approval wait, which also shows as blocked.
//
// The next run (agent_start) clears both. Outside herdr (HERDR_ENV, socket, or
// pane missing), or outside the TUI, it does nothing.
//
// sparks agent spawn loads it with `-e <plugin>/pi/extensions/sparks-api-error-blocked.ts`.
// To load it in every pi session, copy or symlink it into ~/.pi/agent/extensions/.
// pi events used: message_end, agent_settled, agent_start, session_start
// (pi docs/extensions.md, "Respect the runtime lifecycle").
// @ts-nocheck

import net from "node:net";

export const TOKEN = "sparks_api_error";
export const PREFIX = "sparks:api-error: ";
const SOURCE = "sparks:pi";
const MAX_CHARS = 300;

function enabled(): boolean {
  return process.env.HERDR_ENV === "1" && !!process.env.HERDR_SOCKET_PATH && !!process.env.HERDR_PANE_ID;
}

/** The error text of an assistant message that stopped with an error, or undefined. */
export function apiError(message: any): string | undefined {
  if (message?.role !== "assistant" || message?.stopReason !== "error") {
    return undefined;
  }
  const text = typeof message.errorMessage === "string" ? message.errorMessage : "";
  // Providers echo masked keys ("Incorrect API key provided: sk-proj-****abcd"); keep any
  // key-like run out of the herdr label and pane token.
  const line = text.replace(/\s+/g, " ").trim()
    .replace(/\b(sk|xai|key|token)-[A-Za-z0-9_*-]{4,}/gi, "[redacted]")
    .replace(/[A-Za-z0-9_*+/=-]{32,}/g, "[redacted]") || "model request failed";
  return line.length > MAX_CHARS ? `${line.slice(0, MAX_CHARS - 3)}...` : line;
}

function send(request: unknown, timeoutMs = 1000): Promise<boolean> {
  const socketPath = process.env.HERDR_SOCKET_PATH!;
  const endpoint = process.platform === "win32" ? `\\\\.\\pipe\\${socketPath}` : socketPath;
  return new Promise((resolve) => {
    let done = false;
    const socket = net.createConnection(endpoint);
    const finish = (delivered: boolean) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      socket.destroy();
      resolve(delivered);
    };
    const timer = setTimeout(() => finish(false), timeoutMs);
    timer.unref?.();
    socket.on("error", () => finish(false));
    socket.on("connect", () => socket.write(`${JSON.stringify(request)}\n`));
    socket.on("data", () => finish(true));
    socket.on("end", () => finish(false));
  });
}

/** Set the pane token to the error text, or clear it with null. */
export function reportToken(error: string | null): Promise<boolean> {
  return send({
    id: `${SOURCE}:${Date.now()}:${Math.random().toString(36).slice(2)}`,
    method: "pane.report_metadata",
    params: { pane_id: process.env.HERDR_PANE_ID, source: SOURCE, agent: "pi", tokens: { [TOKEN]: error } },
  });
}

export default function (pi) {
  if (!enabled()) {
    return;
  }
  let rootSession = false;
  let lastError: string | undefined;
  let blocked = false;

  pi.on("session_start", (_event, ctx) => {
    // Same gate as herdr's extension: only the TUI session owns the pane.
    rootSession = ctx?.mode === "tui";
  });

  pi.on("agent_start", async () => {
    lastError = undefined;
    if (!blocked) return;
    blocked = false;
    pi.events.emit("herdr:blocked", { active: false });
    await reportToken(null);
  });

  pi.on("message_end", (event) => {
    if (event?.message?.role === "assistant") {
      lastError = apiError(event.message);
    }
  });

  pi.on("agent_settled", async (event) => {
    if (!rootSession || event?.aborted || !lastError || blocked) return;
    blocked = true;
    pi.events.emit("herdr:blocked", { active: true, label: `${PREFIX}${lastError}` });
    await reportToken(lastError);
  });
}

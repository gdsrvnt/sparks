// Per-run completion protocol for sparks agent spawn. herdr's managed extension
// may publish idle first: consumers must wait for sparks_run, not pane state.
// Metadata is acknowledged before herdr:blocked. Failed delivery leaves the
// outcome unknown (spawn keeps the tab and exits nonzero), never implicit ok.
// Loaded via -e; outside a herdr TUI this extension does nothing.
// @ts-nocheck
import net from "node:net";

export const TOKEN = "sparks_api_error";
export const RUN_TOKEN = "sparks_run";
export const PREFIX = "sparks:api-error: ";
const SOURCE = "sparks:pi";

function enabled(): boolean {
  return process.env.HERDR_ENV === "1" && !!process.env.HERDR_SOCKET_PATH && !!process.env.HERDR_PANE_ID;
}

/** Only orchestration categories leave the local pi view, never provider diagnostics. */
export function apiError(message: any): string | undefined {
  if (message?.role !== "assistant" || message?.stopReason !== "error") return undefined;
  const text = typeof message.errorMessage === "string" ? message.errorMessage : "";
  const provider = /^[a-z][a-z0-9_-]{0,39}$/i.test(message.provider ?? "") ? message.provider : "model";
  // Accept only an HTTP error status, not arbitrary numbers from diagnostics.
  // Never copy even a prefix of provider text: credentials can occur anywhere.
  const status = String(message.status ?? message.statusCode ?? "").match(/^[45]\d\d$/)?.[0]
    ?? text.match(/\bHTTP\s+([45]\d\d)\b/i)?.[1];
  return `${provider}${status ? ` HTTP ${status}` : ""} api error: model request failed`;
}

function send(request: any, timeoutMs = 1000): Promise<boolean> {
  const socketPath = process.env.HERDR_SOCKET_PATH!;
  const endpoint = process.platform === "win32" ? `\\\\.\\pipe\\${socketPath}` : socketPath;
  return new Promise((resolve) => {
    let done = false;
    let buffer = "";
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
    socket.on("data", (data) => {
      buffer += data.toString();
      if (!buffer.includes("\n")) return;
      try {
        const reply = JSON.parse(buffer.split("\n")[0]);
        finish(reply.id === request.id && !reply.error && !!reply.result);
      } catch { finish(false); }
    });
    socket.on("end", () => finish(false));
  });
}

export function reportToken(error: string | null, run: string): Promise<boolean> {
  return send({
    id: `${SOURCE}:${Date.now()}:${Math.random().toString(36).slice(2)}`,
    method: "pane.report_metadata",
    params: { pane_id: process.env.HERDR_PANE_ID, source: SOURCE, agent: "pi",
      tokens: { [TOKEN]: error, [RUN_TOKEN]: run } },
  });
}

export default function (pi) {
  if (!enabled()) return;
  let rootSession = false;
  let lastError: string | undefined;
  let blocked = false;
  let seq = 0;
  let activeRun = false;
  const publish = async (error, outcome) => {
    const delivered = await reportToken(error, `${seq}:${outcome}`);
    if (!delivered) console.error("sparks: completion metadata delivery failed; outcome unconfirmed");
    return delivered;
  };
  pi.on("session_start", async (_event, ctx) => {
    rootSession = ctx?.mode === "tui";
    if (rootSession) await publish(null, "ready");
  });
  pi.on("agent_start", async () => {
    if (!rootSession) return;
    // Retry/recovery continuations emit another low-level agent_start before
    // agent_settled. All of them belong to the same submitted logical run.
    if (!activeRun) seq += 1;
    activeRun = true;
    lastError = undefined;
    await publish(null, "running");
    if (blocked) {
      blocked = false;
      pi.events.emit("herdr:blocked", { active: false });
    }
  });
  pi.on("message_end", (event) => {
    if (rootSession && event?.message?.role === "assistant") lastError = apiError(event.message);
  });
  pi.on("agent_settled", async (event) => {
    if (!rootSession) return;
    activeRun = false;
    const error = event?.aborted ? undefined : lastError;
    const delivered = await publish(error ?? null, event?.aborted ? "aborted" : error ? "error" : "ok");
    if (delivered && error && !blocked) {
      blocked = true;
      pi.events.emit("herdr:blocked", { active: true, label: `${PREFIX}${error}` });
    }
  });
}

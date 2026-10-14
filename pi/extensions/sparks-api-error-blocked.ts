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
const MAX_CHARS = 300;

function enabled(): boolean {
  return process.env.HERDR_ENV === "1" && !!process.env.HERDR_SOCKET_PATH && !!process.env.HERDR_PANE_ID;
}

/** Publish a category and sanitized message, never unrestricted provider text. */
export function apiError(message: any): string | undefined {
  if (message?.role !== "assistant" || message?.stopReason !== "error") return undefined;
  const text = typeof message.errorMessage === "string" ? message.errorMessage : "";
  const provider = /^[a-z][a-z0-9_-]{0,39}$/i.test(message.provider ?? "") ? message.provider : "model";
  // Discard the entire tail after a credential label. Values may be short,
  // quoted, contain spaces, or use custom-provider formats. Do not guess length.
  const line = text.replace(/\s+/g, " ").trim()
    .replace(/(?<![A-Za-z0-9])((?:api[\s_-]*)?key|token|bearer|authorization)(?![A-Za-z0-9]).*$/i, "$1 [redacted]")
    .replace(/\b(sk|xai|key|token)-[A-Za-z0-9_*-]+/gi, "[redacted]")
    .replace(/[A-Za-z0-9_*+/=-]{32,}/g, "[redacted]") || "model request failed";
  // Extract textual status only after redaction: a credential like "token: 401"
  // must not be copied back into the category as a putative HTTP status.
  const status = String(message.status ?? message.statusCode ?? "").match(/^[45]\d\d$/)?.[0]
    ?? line.match(/\b([45]\d\d)\b/)?.[1];
  const safe = `${provider}${status ? ` HTTP ${status}` : ""} api error: ${line}`;
  return safe.length > MAX_CHARS ? `${safe.slice(0, MAX_CHARS - 3)}...` : safe;
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
    seq += 1;
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
    const error = event?.aborted ? undefined : lastError;
    const delivered = await publish(error ?? null, event?.aborted ? "aborted" : error ? "error" : "ok");
    if (delivered && error && !blocked) {
      blocked = true;
      pi.events.emit("herdr:blocked", { active: true, label: `${PREFIX}${error}` });
    }
  });
}

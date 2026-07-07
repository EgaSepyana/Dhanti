const PREFIX = "dhanti:pending-message:";

interface PendingMessage {
  message: string;
  model?: string;
}

/** Hands off the first message (and optional model choice) typed on the home
 * composer to the workspace page it just navigated to, so the chat
 * auto-sends it once the conversation is ready — sessionStorage (not a URL
 * param) keeps prompt text out of the address bar/history. */
export function setPendingMessage(workspaceId: string, message: string, model?: string): void {
  const payload: PendingMessage = { message, model };
  sessionStorage.setItem(`${PREFIX}${workspaceId}`, JSON.stringify(payload));
}

export function takePendingMessage(workspaceId: string): PendingMessage | null {
  const key = `${PREFIX}${workspaceId}`;
  const raw = sessionStorage.getItem(key);
  if (raw === null) return null;
  sessionStorage.removeItem(key);
  try {
    return JSON.parse(raw) as PendingMessage;
  } catch {
    return null;
  }
}

import { BRIDGE_CLIENT_SOURCE } from "./bridge-client-source";

/**
 * Enforced by the browser itself (unlike a monkey-patched fetch/WebSocket,
 * this can't be bypassed by iframe-internal JS): blocks all network access
 * except loading the ECharts CDN script tag, which agent-generated dashboards
 * rely on. connect-src covers fetch/XHR/WebSocket/EventSource alike.
 */
const CONTENT_SECURITY_POLICY = [
  "default-src 'none'",
  "script-src 'unsafe-inline' https://cdn.jsdelivr.net",
  "style-src 'unsafe-inline'",
  "img-src data: blob:",
  "font-src data:",
  "connect-src 'none'",
].join("; ");

/** Wraps a runnable artifact's raw HTML (a dashboard's content.entry) with
 * the CSP + Bridge Client needed to run it safely in the Canvas sandbox. */
export function buildCanvasHtml(entryHtml: string): string {
  const cspTag = `<meta http-equiv="Content-Security-Policy" content="${CONTENT_SECURITY_POLICY}">`;
  const bridgeScript = `<script>${BRIDGE_CLIENT_SOURCE}</script>`;

  let html = entryHtml;

  if (html.includes("</head>")) {
    html = html.replace("</head>", `${cspTag}\n</head>`);
  } else if (html.includes("<html")) {
    html = html.replace(/<html([^>]*)>/, `<html$1><head>${cspTag}</head>`);
  } else {
    html = `${cspTag}\n${html}`;
  }

  if (/<body[^>]*>/.test(html)) {
    html = html.replace(/<body([^>]*)>/, `<body$1>${bridgeScript}`);
  } else {
    html = `${bridgeScript}\n${html}`;
  }

  return html;
}

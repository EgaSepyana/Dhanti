import { describe, expect, it } from "vitest";
import { buildCanvasHtml } from "./artifact-loader";

describe("buildCanvasHtml", () => {
  it("injects a CSP meta tag that blocks arbitrary network access", () => {
    const html = buildCanvasHtml("<html><head></head><body><p>hi</p></body></html>");
    expect(html).toMatch(/<meta http-equiv="Content-Security-Policy"/);
    expect(html).toMatch(/connect-src 'none'/);
  });

  it("allows the ECharts CDN script specifically", () => {
    const html = buildCanvasHtml("<html><head></head><body></body></html>");
    expect(html).toMatch(/script-src[^"]*cdn\.jsdelivr\.net/);
  });

  it("injects the bridge client script into the body", () => {
    const html = buildCanvasHtml("<html><head></head><body><p>hi</p></body></html>");
    expect(html).toMatch(/window\.bridge = \{/);
  });

  it("handles documents missing a </head> or <body> tag without throwing", () => {
    expect(() => buildCanvasHtml("<p>bare fragment</p>")).not.toThrow();
    const html = buildCanvasHtml("<p>bare fragment</p>");
    expect(html).toContain("bare fragment");
    expect(html).toMatch(/window\.bridge = \{/);
  });
});

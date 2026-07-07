import re

# Dashboard HTML documents (charts, tables, inline runtime JS) are large —
# the default ai_max_tokens budget is sized for chat replies, not full pages,
# so generation explicitly overrides it with this larger budget.
DASHBOARD_HTML_MAX_TOKENS = 8000

# The only external resource the sandboxed Canvas iframe's CSP allows
# (see frontend/src/lib/canvas/artifact-loader.ts) — any dashboard that
# renders a chart via echarts.init(...) must load this exact tag or the
# call fails at runtime with "echarts is not defined".
ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"


def extract_html(raw: str) -> str:
    """Strip markdown fences from an LLM's HTML response and validate it is
    a genuinely complete document (opening AND closing tags present).

    A streamed response can get cut off — or the model just doesn't close
    its fence — leaving a leading ```html marker stuck in front of
    <!DOCTYPE, or the document truncated mid-way. Both must be rejected
    here rather than silently saved, so callers fall back instead of
    persisting broken HTML.
    """
    raw = raw.strip()
    raw = re.sub(r"^```(?:html)?\s*\n?", "", raw)
    raw = re.sub(r"\n?```\s*$", "", raw)
    raw = raw.strip()
    lowered = raw.lower()
    if "<!doctype" not in lowered and "<html" not in lowered:
        raise ValueError(f"LLM response does not look like an HTML document: {raw[:200]!r}")
    if "</html>" not in lowered:
        raise ValueError(f"LLM response HTML looks truncated (no closing </html>): {raw[-200:]!r}")
    return raw


def ensure_echarts_script(html: str) -> str:
    """Guarantees the ECharts CDN script tag is present whenever the HTML
    actually calls into the echarts API — deterministically, rather than
    relying on the LLM to remember it. This matters most for revisions: a
    dashboard that starts with only table/metric widgets never needed
    ECharts, so its <head> has no CDN tag; if a later revision adds a chart
    widget, the LLM must ALSO add the tag, and nothing enforced that until
    now — the exact gap that let "echarts is not defined" through."""
    if "echarts." not in html or ECHARTS_CDN in html:
        return html

    tag = f'<script src="{ECHARTS_CDN}"></script>'
    if "</head>" in html:
        return html.replace("</head>", f"{tag}\n</head>", 1)
    if re.search(r"<html[^>]*>", html):
        return re.sub(r"(<html[^>]*>)", rf"\1<head>{tag}</head>", html, count=1)
    return f"{tag}\n{html}"

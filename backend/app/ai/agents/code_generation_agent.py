import asyncio
import json
import uuid

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.base_agent import BaseAgent
from app.ai.agents.html_generation_utils import (
    DASHBOARD_HTML_MAX_TOKENS,
    ECHARTS_CDN,
    ensure_echarts_script,
    extract_html,
)
from app.ai.schemas import AgentResult, AgentTask
from app.models.dataset import Dataset
from app.models.widget import Widget
from app.providers.manager import get_llm_for_model
from app.services import duckdb_service

# Same fixed categorical hue order as visualization_tools.CATEGORICAL_PALETTE
# and dashboard-runtime-source.ts's light-mode steps — kept in sync so the
# deterministic template fallback matches the rest of the product.
CATEGORICAL_PALETTE = [
    "#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834",
]

# The dataviz color/form rules below are the same ones this codebase's own
# dashboard-runtime-source.ts and visualization_tools.py encode — repeating
# them here so the LLM-authored page matches the rest of the product instead
# of inventing its own palette per dashboard.
SYSTEM_PROMPT = f"""You are DHANTI's senior frontend engineer — an expert in HTML, CSS, and \
JavaScript who turns a data analyst's dashboard spec into a polished, production-quality, \
single-file HTML dashboard that a real company would ship.

You will be given: a dashboard layout (grid positions) and a list of widgets (id, name, \
title, type, config) describing what to show and where; a few sample rows from the source \
dataset (shape reference only); and any analyst insights explaining the story behind them.

RUNTIME CONTRACT (must follow exactly):
- The page runs inside a sandboxed iframe with no network access except this exact script tag: \
<script src="{ECHARTS_CDN}"></script>. Do not load any other external resource — no fonts, no \
other CDNs, no remote images.
- A `window.bridge` object is injected before your script runs. For EACH widget, call \
`await window.bridge.widget.execute("<widget_id>")` to fetch THAT widget's live data — it \
resolves to `{{ columns, rows, row_count }}`, where `rows` is an array of row objects keyed by \
column name, already shaped for that specific widget by its own query (a metric widget's query \
returns one row with one aggregate column; a chart widget's returns the exact category/value \
columns to plot; a table widget's returns the rows/columns to display). This call hits a live \
backend endpoint and must happen at page load / render time — this is your ONLY source of \
data. Never hardcode, precompute, or embed any row values, aggregates, or chart data directly \
in the HTML/JS you write — not even the sample rows given below, which are shape reference \
only and must never appear in your output. Never call a widget's endpoint with any id other \
than the one it was given.
- Show a brief loading state per widget, then render once its own fetch resolves — one widget's \
failure must not block the others from rendering.
- All JS inline in one <script> tag, all CSS inline in one <style> tag. No imports, no modules, \
no build step, no bundler syntax.

DESIGN QUALITY BAR (non-negotiable):
- Sequential data (magnitude) gets one hue, light-to-dark. Categorical series get a FIXED hue \
order, never cycled or invented: blue, aqua, yellow, green, violet, red, magenta, orange.
  Light mode hex: #2a78d6, #1baf7a, #eda100, #008300, #4a3aa7, #e34948, #e87ba4, #eb6834.
  Dark mode hex:  #3987e5, #199e70, #c98500, #008300, #9085e9, #e66767, #d55181, #d95926.
- Chart chrome — light: surface #fcfcfb, page #f9f9f7, primary ink #0b0b0b, secondary ink \
#52514e, muted/axis #898781, gridline #e1e0d9, border rgba(11,11,11,0.10).
  Dark: surface #1a1a19, page #0d0d0d, primary ink #ffffff, secondary ink #c3c2b7, muted \
#898781, gridline #2c2c2a, border rgba(255,255,255,0.10).
- Status colors are fixed and never reused for a series: good #0ca30c, warning #fab219, \
serious #ec835a, critical #d03b3b.
- Define these as CSS custom properties and support both themes via \
`@media (prefers-color-scheme: dark)` — never a hardcoded single-theme page.
- System sans only: system-ui, -apple-system, "Segoe UI", sans-serif. No serif/display font.
- Never a dual-axis chart (two y-scales) — two measures of different scale become two charts \
or small multiples instead. A legend is present for 2+ series, omitted for a single series.
- Bar is the default for comparing magnitude across categories. Line for trend over time. \
Scatter for correlation between two numeric measures. Pie ONLY for a genuinely small (<=6) \
part-to-whole split — never for a high-cardinality dimension.
- Responsive CSS grid matching the spec's layout intent; consistent card radius/padding/shadow; \
generous whitespace; a visible hover state on interactive elements; a tooltip on every chart.

Respond with ONLY the complete HTML document, starting with <!DOCTYPE html>. No markdown \
fences, no commentary before or after."""


def _widget_container_html(widget: dict) -> tuple[str, str]:
    """Returns (html, container_id) — an empty shell; data is filled in by
    the client-side runtime_js below at render time, never at generation
    time, so the template never bakes in a data snapshot."""
    pos = widget["position"]
    style = (
        f"grid-column: {pos['x'] + 1} / span {pos['w']}; "
        f"grid-row: {pos['y'] + 1} / span {pos['h']};"
    )
    container_id = f"widget-{widget['widget_id']}"
    return (
        f'<div class="widget {widget["type"]}-widget" style="{style}">'
        f'<div class="widget-title">{widget["title"]}</div>'
        f'<div id="{container_id}" class="widget-body">Loading…</div>'
        f"</div>",
        container_id,
    )


def render_dashboard_html(dashboard: dict, widgets_by_id: dict[str, Widget], theme: dict) -> str:
    """Deterministic, template-based fallback: always produces a working
    dashboard shell whose JS fetches each widget's LIVE data via
    `bridge.widget.execute(widget_id)` at render time — same runtime
    contract the LLM-authored path is instructed to follow, just with fixed
    markup instead of a bespoke design. Never executes a query or embeds a
    result at generation time. Used when the LLM-authored path (this
    module's primary path) fails or returns something that isn't valid HTML."""
    widget_htmls = []
    client_widgets = []
    needs_echarts = False
    for w in dashboard["widgets"]:
        widget = widgets_by_id.get(w["widget_id"])
        if widget is None:
            continue
        html, container_id = _widget_container_html(w)
        widget_htmls.append(html)
        if w["type"] == "chart":
            needs_echarts = True
        client_widgets.append(
            {
                "widget_id": w["widget_id"],
                "container_id": container_id,
                "type": w["type"],
                "chart_type": widget.config.get("chart_type", "bar"),
            }
        )

    widgets_html = "\n".join(widget_htmls)
    echarts_script_tag = f'<script src="{ECHARTS_CDN}"></script>' if needs_echarts else ""

    # Runs inside the sandboxed iframe once window.bridge is injected — fetches
    # each widget's data live via bridge.widget.execute, never from a value
    # baked in at generation time.
    runtime_js = f"""
(function() {{
  var CATEGORICAL_PALETTE = {json.dumps(CATEGORICAL_PALETTE)};
  var widgets = {json.dumps(client_widgets)};

  function escapeHtml(value) {{
    return String(value).replace(/[&<>"']/g, function (c) {{
      return {{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }}[c];
    }});
  }}

  function renderMetric(el, columns, rows) {{
    var value = (rows[0] && columns[0]) ? rows[0][columns[0]] : 0;
    var num = Number(value);
    el.innerHTML = '<div class="metric-value">' +
      (isNaN(num) ? escapeHtml(value) : num.toLocaleString(undefined, {{ maximumFractionDigits: 2 }})) +
      '</div>';
  }}

  function renderChart(el, chartType, columns, rows) {{
    el.innerHTML = '';
    var chart = echarts.init(el);
    var catCol = columns[0], valCol = columns[1];
    var categories = rows.map(function (r) {{ return String(r[catCol]); }});
    var values = rows.map(function (r) {{ return r[valCol]; }});
    var option;
    if (chartType === 'pie') {{
      option = {{
        color: CATEGORICAL_PALETTE,
        tooltip: {{ trigger: 'item' }},
        legend: {{ top: 'bottom' }},
        series: [{{ type: 'pie', radius: '60%', data: categories.map(function (c, i) {{ return {{ name: c, value: values[i] }}; }}) }}],
      }};
    }} else {{
      option = {{
        color: CATEGORICAL_PALETTE,
        tooltip: {{ trigger: 'axis' }},
        xAxis: {{ type: 'category', data: categories }},
        yAxis: {{ type: 'value' }},
        series: [{{ type: chartType, data: values }}],
      }};
    }}
    chart.setOption(option);
    window.addEventListener('resize', function () {{ chart.resize(); }});
  }}

  function renderTable(el, columns, rows) {{
    var header = columns.map(function (c) {{ return '<th>' + escapeHtml(c) + '</th>'; }}).join('');
    var body = rows.map(function (row) {{
      return '<tr>' + columns.map(function (c) {{
        return '<td>' + (row[c] != null ? escapeHtml(row[c]) : '') + '</td>';
      }}).join('') + '</tr>';
    }}).join('');
    el.innerHTML = '<table><thead><tr>' + header + '</tr></thead><tbody>' + body + '</tbody></table>';
  }}

  widgets.forEach(function (w) {{
    var el = document.getElementById(w.container_id);
    if (!el) return;
    window.bridge.widget.execute(w.widget_id).then(function (result) {{
      var columns = result.columns || [];
      var rows = result.rows || [];
      if (w.type === 'metric') renderMetric(el, columns, rows);
      else if (w.type === 'chart') renderChart(el, w.chart_type, columns, rows);
      else renderTable(el, columns, rows);
    }}).catch(function (err) {{
      el.textContent = 'Failed to load: ' + (err && err.message ? err.message : 'unknown error');
    }});
  }});
}})();
"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
{echarts_script_tag}
<style>
  body {{ margin: 0; font-family: system-ui, sans-serif; background: {theme.get("mode") == "dark" and "#0b1220" or "#f8fafc"};
          color: {theme.get("mode") == "dark" and "#e2e8f0" or "#1e3a8a"}; }}
  .grid {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: 12px; padding: 16px; }}
  .widget {{ background: white; border-radius: 8px; padding: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: auto; }}
  .widget-title {{ font-size: 13px; font-weight: 600; margin-bottom: 8px; color: #64748b; }}
  .widget-body {{ font-size: 13px; color: #94a3b8; height: calc(100% - 24px); min-height: 200px; }}
  .metric-value {{ font-size: 28px; font-weight: 700; color: {theme.get("primary_color", "#1e40af")}; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: left; padding: 4px 8px; border-bottom: 1px solid #e2e8f0; }}
</style>
</head>
<body>
<div class="grid">
{widgets_html}
</div>
<script>{runtime_js}</script>
</body>
</html>"""


async def _generate_llm_dashboard_html(
    dashboard: dict,
    widgets_by_id: dict[str, Widget],
    dataset: Dataset,
    sample_rows: list[dict],
    insight_text: str | None,
    status_queue: asyncio.Queue | None = None,
    step_id: str | None = None,
    model: str | None = None,
) -> str:
    widgets_desc = [
        {
            "id": str(wid),
            "name": w.name,
            "title": w.title,
            "type": w.type,
            "config": w.config,
        }
        for wid, w in widgets_by_id.items()
    ]
    llm = get_llm_for_model(model)
    user_content = (
        f"Dashboard layout:\n{json.dumps(dashboard)}\n\n"
        f"Widgets (call bridge.widget.execute(widget_id) for each to get its live data):\n"
        f"{json.dumps(widgets_desc)}\n\n"
        f"Dataset '{dataset.name}' sample rows (shape reference only — the actual widget "
        f"queries return differently-shaped data per widget, fetched live; do not embed "
        f"these values in your output):\n"
        f"{json.dumps(sample_rows[:5], default=str)}"
        + (f"\n\nAnalyst insights:\n{insight_text}" if insight_text else "")
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    if status_queue is None:
        raw = await llm.generate(
            messages, model=model, temperature=0.4, max_tokens=DASHBOARD_HTML_MAX_TOKENS
        )
        return ensure_echarts_script(extract_html(raw))

    # Live path: stream chunks straight to the client as they arrive, so the
    # workspace's Canvas can show the agent writing code in real time instead
    # of waiting for the full response before anything appears.
    chunks: list[str] = []
    async for chunk in llm.generate_stream(
        messages, model=model, temperature=0.4, max_tokens=DASHBOARD_HTML_MAX_TOKENS
    ):
        chunks.append(chunk)
        await status_queue.put(("code_delta", {"step_id": step_id, "delta": chunk}))
    return ensure_echarts_script(extract_html("".join(chunks)))


class CodeGenerationAgent(BaseAgent):
    """DHANTI's frontend-design-expert agent — the "developer" that decides
    how to display dashboard_agent's widgets and wires up the API calls —
    and the sole producer of "dashboard" artifacts: turns the layout + widget
    list into a bespoke, polished HTML+CSS+JS document via the LLM, styled
    per the dataviz color/form rules and bound to live data by calling each
    widget's /api/widgets/{id}/handler endpoint through the Bridge API at
    render time. "Dashboard" IS this generated code; it never embeds a data
    snapshot at generation time — the deterministic template fallback (used
    if the LLM call fails or returns something that isn't valid HTML) fetches
    live too, via the exact same bridge.widget.execute contract, so dashboard
    generation never breaks and never goes stale."""

    name = "code_generation_agent"

    async def run(self, task: AgentTask, db: AsyncSession) -> AgentResult:
        dependencies = task.input.get("_dependencies", {})
        dashboard = dependencies.get("dashboard_agent")
        if not dashboard:
            return self._error(task, "code_generation_agent requires a dashboard_agent dependency")

        dataset_id = task.input.get("dataset_id")
        if not dataset_id:
            return self._error(task, "code_generation_agent requires 'dataset_id' in input")
        dataset = await db.get(Dataset, uuid.UUID(str(dataset_id)))
        if dataset is None:
            return self._error(task, f"Dataset '{dataset_id}' not found")

        widgets_by_id: dict[str, Widget] = {}
        for w in dashboard["widgets"]:
            widget = await db.get(Widget, uuid.UUID(str(w["widget_id"])))
            if widget is not None:
                widgets_by_id[w["widget_id"]] = widget

        # Sample rows are LLM context only (so it understands column shapes)
        # — never executed or embedded by the deterministic template path.
        sample_rows: list[dict] = []
        if dataset.data_path:
            try:
                _, sample_rows, _ = await duckdb_service.execute_widget_query(
                    dataset, "SELECT * FROM dataset LIMIT 5"
                )
            except duckdb_service.WidgetQueryError:
                sample_rows = []

        insight_output = dependencies.get("insight_agent")
        insight_text = insight_output.get("text") if insight_output else None
        status_queue = task.input.get("_status_queue")

        html: str
        generated_by = "llm"
        try:
            html = await _generate_llm_dashboard_html(
                dashboard,
                widgets_by_id,
                dataset,
                sample_rows,
                insight_text,
                status_queue=status_queue,
                step_id=task.task_id,
                model=task.input.get("_model"),
            )
        except Exception as exc:  # noqa: BLE001 - any LLM/parsing failure falls back, never aborts the pipeline
            logger.warning(f"code_generation_agent: LLM HTML generation failed, using template fallback | error={exc}")
            html = render_dashboard_html(dashboard, widgets_by_id, dashboard.get("theme", {}))
            generated_by = "template_fallback"

        output = {
            "runtime": "html",
            "entry": html,
            "assets": [],
            "permissions": {"read": True, "write": False, "execute": True},
        }
        return self._success(task, output, artifact_type="dashboard", metadata={"generated_by": generated_by})

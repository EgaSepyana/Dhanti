import re
from dataclasses import dataclass
from enum import Enum

from app.ai.schemas import WorkspaceContext


class ExecutionMode(str, Enum):
    """How much of the AI pipeline a request actually needs. Ordered here
    from cheapest to most expensive; `route()` checks in that rough spirit
    but revision/build keywords are matched first since they're the most
    specific signals and least likely to false-positive."""

    SIMPLE_QUERY = "simple_query"
    SINGLE_AGENT = "single_agent"
    CODE_GENERATION = "code_generation"
    MULTI_AGENT = "multi_agent"


@dataclass
class RoutingDecision:
    mode: ExecutionMode
    agent: str | None = None  # resolved target agent for SINGLE_AGENT/CODE_GENERATION
    reason: str = ""


# Revising an EXISTING artifact ("change the chart to...", "make the title
# bigger", "add that pie chart to the dashboard") — only meaningful when a
# dashboard already exists in the workspace. "add"/"include"/"insert" matter
# as much as the more obviously-editing verbs: without them, "add X to the
# dashboard" fell through to MULTI_AGENT and built a whole new dashboard
# from scratch instead of actually revising the existing one.
_REVISION_PATTERN = re.compile(
    r"\b(change|update|modify|edit|revise|switch|replace|make|add|include|insert|remove|delete)\b.*\b"
    r"(chart|dashboard|widget|color|colour|title|layout|axis)\b",
    re.IGNORECASE,
)

# Building something NEW that needs the full dataset -> insight -> widgets ->
# code pipeline, or a genuinely multi-part analysis (comparison), or ANY
# request for a visual chart. A chart requires visualization_agent, which
# simple_query_engine has no concept of — checked before the simple-query
# pattern below so "top 10 ... as a pie chart" doesn't get misrouted to a
# text-only answer just because "top 10" also looks like an aggregation.
_MULTI_AGENT_PATTERN = re.compile(
    r"\b(dashboard|html app|html application|interactive (visuali[sz]ation|app)|"
    r"executive (dashboard|summary)|build .*(dashboard|app)|"
    r"generate .*(dashboard|html|app)|create .*dashboard|compar(e|ing|ison)|"
    r"chart|plot|graph|visuali[sz]e|visuali[sz]ation|pie|histogram)\b",
    re.IGNORECASE,
)

# A single agent answers these directly — no planning needed to sequence
# multiple agents, and no LLM at all needed to decide which one to call.
_SINGLE_AGENT_PATTERNS: dict[str, re.Pattern] = {
    "document_agent": re.compile(
        r"\b(summari[sz]e|what does .* say|explain .*(document|pdf|report)|"
        r"tell me about (this|the) (document|pdf|report))\b",
        re.IGNORECASE,
    ),
    "insight_agent": re.compile(
        r"\b(generate insights?|give (me )?insights?|key insights?|"
        r"explain (the )?(result|trend|pattern)s?|what (patterns|trends|anomalies))\b",
        re.IGNORECASE,
    ),
}

# Aggregation-shaped questions with one concrete, computable answer — the
# same signal simple_query_engine itself looks for, checked here first so
# routing doesn't cost an LLM call to discover "this needed no LLM call".
_SIMPLE_QUERY_PATTERN = re.compile(
    r"\b(how many|count|total|sum|average|avg|mean|minimum|maximum|min|max|"
    r"highest|lowest|top \d+|bottom \d+|which \w+ (has|had)|group by|sort(ed)? by)\b",
    re.IGNORECASE,
)


def route(prompt: str, context: WorkspaceContext) -> RoutingDecision:
    """Classifies a request into an ExecutionMode using only keyword/regex
    rules — no LLM call. Ambiguous or unmatched requests fall through to
    MULTI_AGENT, the existing full pipeline, so an uncertain classification
    never costs correctness — only the (already-existing) full cost."""
    text = prompt.strip()

    has_dashboard = any(a.get("type") == "dashboard" for a in context.artifacts)
    if has_dashboard and _REVISION_PATTERN.search(text):
        return RoutingDecision(
            ExecutionMode.CODE_GENERATION,
            agent="dashboard_revision_agent",
            reason="revision phrasing + existing dashboard artifact",
        )

    if _MULTI_AGENT_PATTERN.search(text):
        return RoutingDecision(
            ExecutionMode.MULTI_AGENT, reason="dashboard-build/comparison keywords"
        )

    if context.documents and _SINGLE_AGENT_PATTERNS["document_agent"].search(text):
        return RoutingDecision(
            ExecutionMode.SINGLE_AGENT,
            agent="document_agent",
            reason="document summary/explanation request",
        )

    if context.datasets and _SINGLE_AGENT_PATTERNS["insight_agent"].search(text):
        return RoutingDecision(
            ExecutionMode.SINGLE_AGENT,
            agent="insight_agent",
            reason="insight/explanation request",
        )

    if context.datasets and _SIMPLE_QUERY_PATTERN.search(text):
        return RoutingDecision(
            ExecutionMode.SIMPLE_QUERY, reason="aggregation-shaped question"
        )

    return RoutingDecision(
        ExecutionMode.MULTI_AGENT, reason="no confident deterministic match"
    )

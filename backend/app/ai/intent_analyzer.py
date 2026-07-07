import json
import re

from app.ai.schemas import AGENT_NAMES, INTENTS, IntentResult
from app.providers.manager import get_llm_for_model

# Output is one small JSON object (a handful of short fields) — requesting the
# app-wide default (thousands of tokens) here would needlessly eat into a
# provider's tokens-per-minute budget on every single request, since that
# budget is charged against what's requested, not what's actually used.
INTENT_MAX_TOKENS = 300

SYSTEM_PROMPT = f"""You are DHANTI's intent classifier. Classify the user's request about \
their data workspace into a structured JSON object.

Valid intents: {", ".join(INTENTS)}
Valid agent names: {", ".join(AGENT_NAMES)}

Respond with ONLY a JSON object, no markdown fences, no explanation:
{{
  "intent": "<one of the valid intents>",
  "complexity": "simple" | "medium" | "complex",
  "required_agents": [<subset of valid agent names needed to fulfill the request>],
  "required_data": [<names of files/datasets/documents the prompt refers to, if any>]
}}

Guidance:
- a SPECIFIC factual/aggregate question about STRUCTURED data that one query answers exactly \
— "which X has the highest/lowest Y", "what's the average/total/count of...", "how many rows \
where...", a single lookup or comparison of specific values -> dataset_qa -> dataset_qa_agent. \
Prefer this over data_analysis whenever the question has one concrete, queryable answer instead \
of asking for open-ended trends/patterns/a new chart.
- "analyze"/"insights"/"trends"/"patterns" about data (open-ended, not a single-answer question) \
-> data_analysis -> dataset_agent, insight_agent, visualization_agent
- "summarize"/"what does this say" about a document/PDF -> summarize or document_analysis -> document_agent
- "dashboard"/"visualize everything" (no existing dashboard mentioned in context) -> \
dashboard_generation -> file_agent, dataset_agent, insight_agent, visualization_agent, dashboard_agent, code_generation_agent
- "change the chart to.../make the X a Y/update the dashboard/add that chart to the dashboard" \
referring to an EXISTING dashboard already listed in workspace context artifacts -> \
dashboard_revision -> dashboard_revision_agent
- "chart"/"plot"/"graph" alone -> data_analysis -> dataset_agent, visualization_agent
- a plain question about a document's content (not structured data) -> question_answer -> document_agent
- comparing two datasets/files -> compare -> dataset_agent, insight_agent
"""


def _extract_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {raw!r}")
    return json.loads(match.group(0))


async def analyze_intent(prompt: str, context_summary: str, model: str | None = None) -> IntentResult:
    llm = get_llm_for_model(model)
    raw = await llm.generate(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Workspace context:\n{context_summary}\n\nUser prompt: {prompt}",
            },
        ],
        model=model,
        temperature=0.0,
        max_tokens=INTENT_MAX_TOKENS,
    )
    data = _extract_json(raw)
    return IntentResult(**data)

"""Recall -> Reason -> Retain loop for incident analysis using Groq and Hindsight.

analyze_incident() runs a memory-less baseline and a Hindsight-grounded
evaluation in parallel so the UI can contrast them. save_resolution() writes
the confirmed outcome back to Hindsight so the next similar incident recalls it.
"""
import re
import time
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI

import hindsight_client
from config import AGENT_MODEL, GROQ_API_KEY

# Initialize Groq client using its OpenAI-compatible endpoint
_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    timeout=120.0,
)

BASELINE_SYSTEM = (
    "You are a site reliability engineer. Given a raw production log, explain what is "
    "likely wrong and how to troubleshoot it."
)

HINDSIGHT_SYSTEM = """You are an incident responder for this organization's production platform.
You are given a raw production log and memories recalled from this team's past postmortems.
Use the memories when they match: name the matching incident id and reuse the fix that worked.
If no memory matches, say so and reason from the log alone. Do not invent past incidents.

Answer with exactly these three markdown sections and nothing else:
## Primary Root Cause
## Predicted Blast Radius
## Recommended Runbook Action"""

SECTIONS = {
    "Primary Root Cause": "root_cause",
    "Predicted Blast Radius": "blast_radius",
    "Recommended Runbook Action": "runbook_action",
}


def _ask(system, user):
    """One Groq call. Returns (text, error); never raises, so one failure can't sink both panels."""
    try:
        response = _client.chat.completions.create(
            model=AGENT_MODEL,
            max_tokens=4000,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
        )
    except Exception as exc:
        err_msg = str(exc)
        if "authentication" in err_msg.lower() or "api key" in err_msg.lower():
            return "", "Groq rejected the API key. Set GROQ_API_KEY correctly in your .env file."
        elif "model" in err_msg.lower() or "not found" in err_msg.lower():
            return "", f"Model '{AGENT_MODEL}' not found on Groq. Set AGENT_MODEL in .env to a valid model id."
        else:
            return "", f"Groq LLM call failed: {err_msg}"

    choice = response.choices[0]
    if getattr(choice, "finish_reason", None) == "content_filter":
        return "", "The model declined to analyze this log due to content filters."
    
    text = choice.message.content or ""
    return text, None


def _parse_sections(text):
    """Split the '## Heading' answer into the three named fields ('' if a section is missing)."""
    parts = re.split(r"^##\s*(.+?)\s*$", text, flags=re.MULTILINE)
    found = {parts[i].strip(): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
    return {key: found.get(heading, "") for heading, key in SECTIONS.items()}


def _format_memories(memories):
    if not memories:
        return "No relevant past postmortems were found."
    lines = []
    for m in memories:
        source = (m.get("metadata") or {}).get("incident_id") or m.get("document_id") or "unknown"
        lines.append(f"- [{source}] {m.get('text', '')}")
    return "\n".join(lines)


def _baseline(incoming_log):
    start = time.perf_counter()
    text, error = _ask(BASELINE_SYSTEM, f"<log>\n{incoming_log}\n</log>")
    return {"text": text, "error": error, "latency_s": round(time.perf_counter() - start, 2)}


def _with_memory(incoming_log):
    start = time.perf_counter()
    memories = hindsight_client.recall_memory(hindsight_client.BANK_ID, incoming_log)  # Recall
    prompt = (
        f"<past_postmortems>\n{_format_memories(memories)}\n</past_postmortems>\n\n"
        f"<log>\n{incoming_log}\n</log>"
    )
    text, error = _ask(HINDSIGHT_SYSTEM, prompt)  # Reason
    return {
        **_parse_sections(text),
        "text": text,
        "memories": memories,
        "error": error,
        "latency_s": round(time.perf_counter() - start, 2),
    }


def analyze_incident(incoming_log):
    """Run the baseline and Hindsight evaluations in parallel.

    Returns {"baseline": {text, error, latency_s},
             "hindsight": {root_cause, blast_radius, runbook_action, text, memories, error, latency_s}}.
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        baseline = pool.submit(_baseline, incoming_log)
        hindsight = pool.submit(_with_memory, incoming_log)
        return {"baseline": baseline.result(), "hindsight": hindsight.result()}


def save_resolution(incident_id, log, root_cause, cascade, runbook_fix=None):
    """Retain a resolved incident so future recalls can suggest its fix. Returns True on success.

    cascade may be a list of services in propagation order or a free-text description.
    """
    cascade_text = " -> ".join(cascade) if isinstance(cascade, (list, tuple)) else str(cascade)
    content = (
        f"Postmortem {incident_id}: resolved incident.\n"
        f"Cascade: {cascade_text}\n"
        f"Root cause: {root_cause}\n"
        + (f"Fix that resolved it: {runbook_fix}\n" if runbook_fix else "")
        + f"Raw log excerpt:\n{log[:1500]}"
    )
    return hindsight_client.retain_memory(  # Retain
        hindsight_client.BANK_ID,
        content,
        metadata={"incident_id": incident_id, "source": "agent_resolution"},
        document_id=incident_id,
    )


if __name__ == "__main__":
    parsed = _parse_sections("## Primary Root Cause\nA\n\n## Predicted Blast Radius\nB -> C\n## Recommended Runbook Action\n1. x\n2. y")
    assert parsed == {"root_cause": "A", "blast_radius": "B -> C", "runbook_action": "1. x\n2. y"}, parsed
    assert _parse_sections("no headings")["root_cause"] == ""
    assert "[INC-1]" in _format_memories([{"text": "t", "metadata": {"incident_id": "INC-1"}}])
    print("self-check ok")
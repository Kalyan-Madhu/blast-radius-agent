"""Blast Radius: incident response dashboard contrasting a memory-less LLM with a Hindsight-backed agent."""
import json
import re
from pathlib import Path

import streamlit as st

from agent_engine import analyze_incident, save_resolution
from graph_visualizer import load_topology, render_topology

st.set_page_config(page_title="Blast Radius | Incident Response Agent", page_icon="🚨", layout="wide")

st.markdown("""
<style>
.block-container { padding-top: 2rem; max-width: 1600px; }
h1, h2, h3 { letter-spacing: -0.01em; }
.panel-title { font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
               color: #8B949E; margin-bottom: 0.25rem; }
.card { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 0.75rem; }
.card.red    { border-left: 4px solid #E74C3C; }
.card.orange { border-left: 4px solid #F39C12; }
.card.green  { border-left: 4px solid #2ECC71; }
.card h4 { margin: 0 0 0.5rem 0; font-size: 0.95rem; color: #E6EDF3; }
.memory { background: #0D1117; border: 1px solid #30363D; border-radius: 6px; padding: 0.5rem 0.75rem;
          margin-bottom: 0.4rem; font-size: 0.85rem; color: #C9D1D9; }
.memory b { color: #2ECC71; }
div[data-testid="stMetric"] { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 0.75rem 1rem; }
div[data-testid="stMetricValue"] { color: #2ECC71; }
.stTabs [data-baseweb="tab"] { font-weight: 600; }
code { font-size: 0.78rem !important; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_incidents():
    return json.loads((Path(__file__).with_name("data") / "incidents.json").read_text(encoding="utf-8"))


@st.cache_resource
def topology():
    return load_topology()


def services_mentioned(text, graph):
    """Service ids the model named in its blast-radius answer, in topology order."""
    return [s for s in graph.nodes if re.search(rf"\b{re.escape(s)}\b", text or "")]


def card(title, body, tone):
    st.markdown(f'<div class="card {tone}"><h4>{title}</h4></div>', unsafe_allow_html=True)
    st.markdown(body or "_No answer returned._")


graph = topology()
incidents = load_incidents()
results = st.session_state.setdefault("results", {})
saved = st.session_state.setdefault("saved", set())

# ─── Sidebar: ROI assumptions ─────────────────────────────────────────────────
with st.sidebar:
    st.header("ROI assumptions")
    cost_per_min = st.number_input("Downtime cost ($ / minute)", min_value=0, value=5600, step=100,
                                   help="Industry benchmark often cited from Gartner: ~$5,600/min. Replace with your own.")
    mttr_baseline = st.number_input("MTTR, generic troubleshooting (min)", min_value=1, value=90, step=5)
    mttr_memory = st.number_input("MTTR, with a recalled runbook (min)", min_value=1, value=25, step=5)
    st.caption("Savings are only credited when Hindsight recalls a matching past postmortem.")

st.title("🚨 Blast Radius: Incident Response Agent")
st.caption("Recall → Reason → Retain. The same LLM, with and without organizational memory.")

left, right = st.columns([1, 1.15], gap="large")

# ─── Left: the problem ────────────────────────────────────────────────────────
with left:
    st.markdown('<div class="panel-title">Live incident stream</div>', unsafe_allow_html=True)
    by_id = {i["id"]: i for i in incidents}
    inc_id = st.selectbox(
        "Incoming alert",
        list(by_id),
        format_func=lambda i: f"{by_id[i]['timestamp'][:16].replace('T', ' ')}  ·  {by_id[i]['service']}  ·  {i}",
        label_visibility="collapsed",
    )
    incident = by_id[inc_id]
    result = results.get(inc_id)

    st.code(incident["raw_log"], language="log", height=260)

    failing = [incident["service"]]
    predicted = []
    if result:
        predicted = [s for s in services_mentioned(result["hindsight"]["blast_radius"], graph) if s not in failing]
    st.markdown('<div class="panel-title">Service topology</div>', unsafe_allow_html=True)
    st.caption("🔴 alerting service  ·  🟠 predicted at-risk (after diagnosis)  ·  🟢 healthy. Arrows point caller → dependency.")
    st.iframe(render_topology(failing=failing, at_risk=predicted), height=620)

    if st.button("🔍 Diagnose", type="primary", width="stretch"):
        with st.spinner("Running baseline and Hindsight evaluations in parallel..."):
            results[inc_id] = analyze_incident(incident["raw_log"])
        st.rerun()

# ─── Right: the solution & learning curve ─────────────────────────────────────
with right:
    st.markdown('<div class="panel-title">Diagnosis & learning curve</div>', unsafe_allow_html=True)

    if not result:
        st.info("Pick an incident and press **Diagnose** to compare a memory-less LLM against the Hindsight-backed agent.")
        st.stop()

    base, mem = result["baseline"], result["hindsight"]
    memories = mem["memories"]
    # ponytail: "matched" = the answer cites a past incident id; swap for a recall relevance score if Hindsight exposes one.
    cited = sorted(set(re.findall(r"INC-\d{4}-\d{4}-\d{3}", mem["text"])) - {inc_id})
    matched = bool(cited) and not mem["error"]
    saved_usd = (mttr_baseline - mttr_memory) * cost_per_min if matched else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("Downtime cost saved", f"${saved_usd:,.0f}",
              delta=f"{mttr_baseline - mttr_memory} min faster via {cited[0]}" if matched else "no matching memory",
              delta_color="normal" if matched else "off")
    k2.metric("Past postmortems recalled", len(memories))
    k3.metric("Predicted blast radius", f"{len(predicted)} services" if predicted else "n/a")

    tab_base, tab_mem = st.tabs(["❌ Without Memory", "🧠 With Hindsight Memory"])

    with tab_base:
        st.caption(f"Same model, log only, no organizational context · {base['latency_s']}s")
        if base["error"]:
            st.error(base["error"])
        else:
            st.markdown(base["text"])

    with tab_mem:
        st.caption(f"Recall from bank `sre-blast-radius` → reason over matches · {mem['latency_s']}s")
        if mem["error"]:
            st.error(mem["error"])
        with st.expander(f"Recalled memory snippets ({len(memories)})", expanded=True):
            if not memories:
                st.write("No matching postmortems in memory yet. Save a resolution below to teach the agent.")
            for m in memories:
                src = (m.get("metadata") or {}).get("incident_id") or m.get("document_id") or "derived observation"
                st.markdown(f'<div class="memory"><b>{src}</b> · {m.get("text", "")}</div>', unsafe_allow_html=True)
        if not mem["error"]:
            card("Primary root cause", mem["root_cause"], "red")
            card("Predicted blast radius", mem["blast_radius"], "orange")
            card("Recommended runbook action", mem["runbook_action"], "green")

    # ─── Retain: close the loop ───────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="panel-title">Confirm & teach the agent</div>', unsafe_allow_html=True)
    if inc_id in saved:
        st.success(f"{inc_id} is stored in Hindsight. The next similar alert will recall this resolution.")
    else:
        st.caption("Edit if the on-call engineer found something different, then save. Future diagnoses recall this.")
        root_cause = st.text_area("Confirmed root cause", mem["root_cause"], height=110)
        runbook = st.text_area("Fix that resolved it", mem["runbook_action"], height=110)
        cascade = [*failing, *predicted] if predicted else incident["cascade_pattern"]["path"]
        if st.button("💾 Save resolution to Hindsight", width="stretch", disabled=not root_cause.strip()):
            with st.spinner("Retaining postmortem..."):
                ok = save_resolution(inc_id, incident["raw_log"], root_cause, cascade, runbook_fix=runbook)
            if ok:
                saved.add(inc_id)
                st.rerun()
            st.error("Could not reach Hindsight. The resolution was not saved; check the logs and retry.")

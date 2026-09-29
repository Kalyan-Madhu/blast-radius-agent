"""Blast Radius: incident command center contrasting a memory-less LLM with a Hindsight-backed agent."""
import html
import json
import re
from pathlib import Path

import streamlit as st

from agent_engine import analyze_incident, save_resolution
from config import AGENT_MODEL
from graph_visualizer import load_topology, render_topology
from hindsight_client import BANK_ID

st.set_page_config(page_title="Blast Radius | Incident Command", page_icon="🚨", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
:root { --bg:#0e1117; --card:#161b22; --border:#262c36; --muted:#8b949e; --text:#e6edf3;
        --amber:#f59e0b; --red:#f85149; --green:#3fb950; --purple:#a371f7; }
html, body, [class*="css"], .stMarkdown, button, input, textarea, select {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
code, pre, .stCode { font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace !important; }
.stApp { background: var(--bg); }
/* Streamlit's fixed top bar is ~3.75rem tall; clear it so the brand row isn't hidden underneath. */
.block-container { padding-top: 4.5rem; padding-bottom: 3rem; max-width: 1640px; }
div[data-testid="stColumn"], div[data-testid="stVerticalBlock"] { min-width: 0; }
.stMarkdown, .stCaption, .stAlert, [data-testid="stExpander"] { overflow-wrap: break-word; word-break: break-word; }
.stMarkdown pre, .stMarkdown pre code { white-space: pre-wrap !important; overflow-wrap: anywhere; }
.stMarkdown code { white-space: pre-wrap; overflow-wrap: anywhere; }
.stMarkdown table { display: block; max-width: 100%; overflow-x: auto; }
.stMarkdown td, .stMarkdown th { overflow-wrap: anywhere; }
h1, h2, h3, h4 { letter-spacing: -0.02em; color: var(--text); }
code { font-size: 0.78rem !important; }

.brand { display:flex; flex-wrap:wrap; align-items:center; gap:.5rem .75rem; margin-bottom:.35rem; }
.brand h1 { font-size:1.6rem; font-weight:700; line-height:1.3; margin:0; padding:0 !important; }
.brand h1 a, .brand h1 span[data-testid="stHeaderActionElements"] { display:none; }
.brand .env { white-space:nowrap; font-size:.7rem; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:var(--muted);
              border:1px solid var(--border); border-radius:999px; padding:.15rem .6rem; }
.tagline { color:var(--muted); font-size:.9rem; line-height:1.5; margin-bottom:1.25rem; }
.section { font-size:.72rem; font-weight:600; text-transform:uppercase; letter-spacing:.1em; color:var(--muted);
           margin:1.25rem 0 .5rem; }

.tile { height:100%; min-width:0; background:var(--card); border:1px solid var(--border); border-radius:10px; padding:.9rem 1.1rem;
        transition:border-color .2s ease, transform .2s ease; }
.tile:hover { border-color:#3a4250; transform:translateY(-1px); }
.tile .label { font-size:.7rem; font-weight:600; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }
.tile .value { font-size:1.15rem; font-weight:600; color:var(--text); margin:.3rem 0 .15rem;
               line-height:1.35; overflow-wrap:anywhere; }
.tile .sub { font-size:.78rem; color:var(--muted); overflow-wrap:anywhere; }
.dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:.45rem; vertical-align:middle; }
.dot.green { background:var(--green); box-shadow:0 0 8px var(--green); }
.dot.amber { background:var(--amber); box-shadow:0 0 8px var(--amber); }
.dot.red   { background:var(--red);   box-shadow:0 0 8px var(--red); }
.dot.gray  { background:#484f58; }

.pill { display:inline-block; font-size:.68rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase;
        border-radius:999px; padding:.18rem .6rem; border:1px solid; }
.pill.amber  { color:var(--amber);  border-color:rgba(245,158,11,.4); background:rgba(245,158,11,.08); }
.pill.purple { color:var(--purple); border-color:rgba(163,113,247,.4); background:rgba(163,113,247,.08); }
.pill.green  { color:var(--green);  border-color:rgba(63,185,80,.4);  background:rgba(63,185,80,.08); }
.panel-head { display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:.4rem .75rem; margin-bottom:.35rem; }
.panel-head h3 { font-size:1.05rem; font-weight:600; margin:0; padding:0; }
.panel-meta { font-size:.78rem; color:var(--muted); margin-bottom:.75rem; overflow-wrap:anywhere; }
.pill { white-space:nowrap; }

div[class*="st-key-panel_"], div[class*="st-key-sim_"] {
  background:var(--card); border:1px solid var(--border); border-radius:12px; padding:1.1rem 1.25rem; }
.st-key-panel_baseline { border-top:3px solid var(--amber) !important;
                         box-shadow:inset 0 40px 60px -40px rgba(245,158,11,.10); }
.st-key-panel_hindsight { border-top:3px solid var(--purple) !important;
                          box-shadow:inset 0 40px 60px -40px rgba(163,113,247,.14); }

.card { background:var(--bg); border:1px solid var(--border); border-radius:8px; padding:.6rem .9rem; margin:.6rem 0 .25rem; }
.card.red    { border-left:3px solid var(--red); }
.card.orange { border-left:3px solid var(--amber); }
.card.green  { border-left:3px solid var(--green); }
.card h4 { margin:0; font-size:.8rem; font-weight:600; text-transform:uppercase; letter-spacing:.06em; color:var(--text); }
.memory { overflow-wrap:anywhere; background:var(--bg); border:1px solid var(--border); border-left:3px solid var(--purple); border-radius:6px;
          padding:.5rem .75rem; margin-bottom:.4rem; font-size:.84rem; color:#c9d1d9; }
.memory b { color:var(--purple); }

div[data-testid="stMetric"] { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:.8rem 1rem; }
div[data-testid="stMetricValue"] { color:var(--green); }
div[data-testid="stMetricValue"] > div, div[data-testid="stMetricDelta"] > div { white-space:normal; overflow-wrap:anywhere; }
.stButton button { border-radius:8px; font-weight:600; transition:transform .15s ease, box-shadow .15s ease, filter .15s ease; }
.stButton button:hover { transform:translateY(-1px); box-shadow:0 6px 20px -6px rgba(163,113,247,.55); filter:brightness(1.08); }
.stButton button:active { transform:translateY(0); }
div[data-baseweb="select"] > div { background:var(--card); border-color:var(--border); transition:border-color .15s ease; }
div[data-baseweb="select"] > div:hover { border-color:var(--purple); }
details { border-color:var(--border) !important; border-radius:8px !important; }
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


def section(title):
    st.markdown(f'<div class="section">{title}</div>', unsafe_allow_html=True)


def tile(col, label, value, sub, dot="gray"):
    col.markdown(f'<div class="tile"><div class="label">{label}</div>'
                 f'<div class="value"><span class="dot {dot}"></span>{html.escape(value)}</div>'
                 f'<div class="sub">{html.escape(sub)}</div></div>', unsafe_allow_html=True)


def panel_head(title, pill, tone, meta):
    st.markdown(f'<div class="panel-head"><h3>{title}</h3><span class="pill {tone}">{pill}</span></div>'
                f'<div class="panel-meta">{meta}</div>', unsafe_allow_html=True)


def card(title, body, tone):
    st.markdown(f'<div class="card {tone}"><h4>{title}</h4></div>', unsafe_allow_html=True)
    st.markdown(body or "_No answer returned._")


def scenario_label(inc):
    kind = inc["cascade_pattern"]["type"].replace("-", " ").capitalize()
    return f"{kind}  ·  {inc['service']}  ·  {inc['id']}"


graph = topology()
incidents = load_incidents()
by_id = {i["id"]: i for i in incidents}
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

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown('<div class="brand"><h1>🚨 Blast Radius</h1><span class="env">Incident Command · prod</span></div>'
            '<div class="tagline">Recall → Reason → Retain. The same LLM, with and without organizational memory.</div>',
            unsafe_allow_html=True)
telemetry = st.container()  # filled once the selected incident's result is known

# ─── Incident simulator ───────────────────────────────────────────────────────
section("Incident simulator")
sim_left, sim_right = st.columns([1, 1.1], gap="medium")

with sim_left, st.container(key="sim_log"):
    inc_id = st.selectbox("Preset enterprise incident", list(by_id), format_func=lambda i: scenario_label(by_id[i]))
    incident = by_id[inc_id]
    st.caption(f"Alert fired {incident['timestamp'][:16].replace('T', ' ')} UTC on `{incident['service']}`")
    st.code(incident["raw_log"], language="log", height=340, wrap_lines=True)
    if st.button("⚡ Run diagnosis", type="primary", width="stretch"):
        with st.status("Dispatching incident to agents…", expanded=True) as status:
            st.write(f"🧠 Recalling past postmortems from Hindsight bank `{BANK_ID}`…")
            st.write(f"⚙️ Reasoning with `{AGENT_MODEL}` on Groq: baseline and memory-grounded, in parallel…")
            results[inc_id] = analyze_incident(incident["raw_log"])
            status.update(label="Diagnosis complete", state="complete")
        st.rerun()

result = results.get(inc_id)
failing = [incident["service"]]
predicted = []
if result:
    predicted = [s for s in services_mentioned(result["hindsight"]["blast_radius"], graph) if s not in failing]

with sim_right, st.container(key="sim_topology"):
    st.markdown("**Service topology**")
    st.caption("🔴 alerting  ·  🟠 predicted at-risk (after diagnosis)  ·  🟢 healthy. Arrows point caller → dependency.")
    st.iframe(render_topology(failing=failing, at_risk=predicted), height=470)

# ─── Telemetry bar ────────────────────────────────────────────────────────────
with telemetry:
    t1, t2, t3, t4 = st.columns(4)
    tile(t1, "Active model", AGENT_MODEL, "Groq · OpenAI-compatible API", "green")
    if not result:
        tile(t2, "Hindsight memory", "Standby", f"bank {BANK_ID}", "gray")
        tile(t3, "Recall latency", "—", "awaiting first diagnosis")
        tile(t4, "System health", "Standby", "no diagnosis run yet", "gray")
    else:
        base, mem = result["baseline"], result["hindsight"]
        n = len(mem["memories"])
        # hindsight_client returns [] both on no-match and on outage, so 0 is ambiguous by design.
        tile(t2, "Hindsight memory", f"{n} recalled" if n else "No matches",
             f"bank {BANK_ID}" if n else "empty bank or unreachable", "green" if n else "amber")
        tile(t3, "Recall latency", f"{mem.get('recall_s', '—')} s", f"end-to-end memory path {mem['latency_s']} s",
             "green")
        errors = [e for e in (base["error"], mem["error"]) if e]
        tile(t4, "System health", "Degraded" if errors else "Operational",
             errors[0][:60] if errors else "baseline + memory agents OK", "red" if errors else "green")

if not result:
    st.info("Pick a preset incident and press **Run diagnosis** to compare a memory-less LLM against the Hindsight-backed agent.")
    st.stop()

base, mem = result["baseline"], result["hindsight"]
memories = mem["memories"]
# ponytail: "matched" = the answer cites a past incident id; swap for a recall relevance score if Hindsight exposes one.
cited = sorted(set(re.findall(r"INC-\d{4}-\d{4}-\d{3}", mem["text"])) - {inc_id})
matched = bool(cited) and not mem["error"]
saved_usd = (mttr_baseline - mttr_memory) * cost_per_min if matched else 0

# ─── Impact ───────────────────────────────────────────────────────────────────
section("Impact")
k1, k2, k3 = st.columns(3)
k1.metric("Downtime cost saved", f"${saved_usd:,.0f}",
          delta=f"{mttr_baseline - mttr_memory} min faster via {cited[0]}" if matched else "no matching memory",
          delta_color="normal" if matched else "off")
k2.metric("Past postmortems recalled", len(memories))
k3.metric("Predicted blast radius", f"{len(predicted)} services" if predicted else "n/a")

# ─── Dual-panel comparison ────────────────────────────────────────────────────
section("Diagnosis comparison")
col_base, col_mem = st.columns(2, gap="medium")

with col_base, st.container(key="panel_baseline"):
    panel_head("Without Memory", "Baseline", "amber",
               f"Same model, log only, no organizational context · {base['latency_s']}s")
    if base["error"]:
        st.error(base["error"])
    else:
        st.markdown(base["text"])

with col_mem, st.container(key="panel_hindsight"):
    panel_head("With Hindsight Memory", "Memory-grounded", "purple",
               f"Recall from bank <code>{BANK_ID}</code> → reason over matches · {mem['latency_s']}s")
    if mem["error"]:
        st.error(mem["error"])
    with st.expander(f"Recalled memory snippets ({len(memories)})", expanded=True):
        if not memories:
            st.write("No matching postmortems in memory yet. Save a resolution below to teach the agent.")
        for m in memories:
            src = (m.get("metadata") or {}).get("incident_id") or m.get("document_id") or "derived observation"
            st.markdown(f'<div class="memory"><b>{html.escape(src)}</b> · {html.escape(m.get("text", ""))}</div>',
                        unsafe_allow_html=True)
    if not mem["error"]:
        card("Primary root cause", mem["root_cause"], "red")
        card("Predicted blast radius", mem["blast_radius"], "orange")
        card("Recommended runbook action", mem["runbook_action"], "green")

# ─── Retain: close the loop ───────────────────────────────────────────────────
section("Confirm & teach the agent")
if inc_id in saved:
    st.success(f"{inc_id} is stored in Hindsight. The next similar alert will recall this resolution.")
else:
    st.caption("Edit if the on-call engineer found something different, then save. Future diagnoses recall this.")
    r1, r2 = st.columns(2, gap="medium")
    root_cause = r1.text_area("Confirmed root cause", mem["root_cause"], height=130)
    runbook = r2.text_area("Fix that resolved it", mem["runbook_action"], height=130)
    cascade = [*failing, *predicted] if predicted else incident["cascade_pattern"]["path"]
    if st.button("💾 Save resolution to Hindsight", width="stretch", disabled=not root_cause.strip()):
        with st.spinner("Retaining postmortem in Hindsight…"):
            ok = save_resolution(inc_id, incident["raw_log"], root_cause, cascade, runbook_fix=runbook)
        if ok:
            saved.add(inc_id)
            st.rerun()
        st.error("Could not reach Hindsight. The resolution was not saved; check the logs and retry.")

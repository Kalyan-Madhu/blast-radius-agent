<div align="center">

# 🔴 Blast Radius: SRE Incident Response Agent
### *The self-improving SRE agent that remembers past postmortems so you never debug the same outage twice.*

[![Built with Hindsight](https://img.shields.io/badge/Memory-Hindsight-blueviolet?style=for-the-badge)](https://hindsight.vectorize.io/)
[![Powered by Groq](https://img.shields.io/badge/Inference-Groq-orange?style=for-the-badge)](https://groq.com/)
[![Streamlit UI](https://img.shields.io/badge/Frontend-Streamlit-red?style=for-the-badge)](https://streamlit.io/)

</div>

---

## 🎯 The Problem
When production goes down under midnight alerts, every second counts. Traditional AI assistants and stateless chatbots are completely blind to organizational history—they give the exact same generic troubleshooting advice during every outage, forcing senior SREs to dig through months of stale Jira tickets and scattered Slack post-mortems under immense pressure.

## 💡 The Solution: Persistent Memory for Incident Response
**Blast Radius** is an intelligent Site Reliability Engineering agent powered by **Hindsight** memory. Unlike stateless agents that forget everything the moment a chat session closes, Blast Radius **learns from every production outage**.

When an incident hits, it triggers a parallel dual-panel evaluation:
1. **Without Memory (Baseline):** Standard generic LLM diagnosis.
2. **With Hindsight Memory:** Instantly recalls historical post-mortems, maps out cascading service failures, and surfaces the exact proven runbook fix that resolved the issue previously.

Once the incident is resolved, the agent **retains** the outcome back into its memory bank, ensuring the entire engineering organization gets smarter with every single outage.

---

## 🔄 The Recall-Reason-Retain Workflow

* **1. Recall:** Automatically queries Hindsight vector memory banks to surface relevant historical context and past incident IDs based on incoming error logs.
* **2. Reason:** Passes the log and recalled organizational history into Groq using the **`openai/gpt-oss-20b`** model to generate precise root causes, blast radiuses, and runbook actions.
* **3. Retain:** Writes confirmed resolutions and cascading propagation patterns back into Hindsight for future recall.

---

## ✨ Key Features

* **Dual-Panel Contrast View:** Side-by-side UI comparing a memory-less baseline against a Hindsight-grounded expert response.
* **Ultra-Low Latency Inference:** Leverages Groq's high-speed hardware (`openai/gpt-oss-20b`) for instantaneous root-cause analysis during high-stress outages.
* **Propagation Cascade Mapping:** Predicts downstream service failures before dependent microservices crash.

---

## 🛠️ Tech Stack

* **Core Logic:** Python, OpenAI-compatible SDK
* **Memory Layer:** Hindsight (by Vectorize)
* **LLM Inference:** Groq (`openai/gpt-oss-20b`)
* **Frontend UI:** Streamlit

---

## 🚀 Getting Started & Local Installation

### 1. Clone the repository
```bash
git clone https://github.com/Kalyan-Madhu/blast-radius-agent.git
cd blast-radius-agent
```

### 2. Install dependencies (Python 3.10+)
```bash
pip install -r requirements.txt
```

### 3. Configure keys
Copy `.env.example` to `.env` and fill in:

| Variable | Required | Notes |
|---|---|---|
| `GROQ_API_KEY` | yes | From [console.groq.com](https://console.groq.com/keys) |
| `HINDSIGHT_API_KEY` | yes | From [Hindsight](https://hindsight.vectorize.io/) |
| `AGENT_MODEL` | no | Defaults to `openai/gpt-oss-20b`; any chat model your key lists at `https://api.groq.com/openai/v1/models` |
| `HINDSIGHT_BASE_URL` | no | Defaults to Hindsight Cloud; set for a self-hosted server |

### 4. Seed the memory bank
Stores the first 5 historical postmortems from `data/incidents.json` in the `sre-blast-radius` bank:
```bash
python seed_memory.py
```

### 5. Run the dashboard
```bash
streamlit run app.py
```
Pick a preset incident, press **Run diagnosis**, then save the confirmed resolution so the next similar alert recalls it.

---

## 📐 How the numbers work

* **Recall relevance:** Hindsight returns ~100 ranked facts per query. Only facts with `scores.semantic >= 0.75` are kept (`MIN_SEMANTIC_SCORE` in `hindsight_client.py`), so an unrelated incident recalls nothing. Recall queries are cut to the first 1000 characters of the log because Hindsight rejects queries over 500 tokens.
* **Downtime cost saved:** credited only when a relevant memory is recalled. Cost per minute comes from the most critical impacted service (`criticality` in `data/topology.json`: tier-0 $10k, tier-1 $5k, tier-2 $1k); generic MTTR is 30 min + 15 min per impacted service, versus 25 min with a recalled runbook. All of these are editable in the sidebar.

## 🗂️ Project layout

| File | Purpose |
|---|---|
| `app.py` | Streamlit incident command center |
| `agent_engine.py` | Recall → Reason → Retain loop; baseline and memory-grounded Groq calls in parallel |
| `hindsight_client.py` | Hindsight REST wrapper (retain / recall with relevance filter) |
| `graph_visualizer.py` | pyvis service-topology graph with blast-radius colouring |
| `seed_memory.py` | Seeds historical postmortems into Hindsight |
| `config.py` | Loads and validates `.env` |
| `data/incidents.json`, `data/topology.json` | Demo incidents and service dependency graph |

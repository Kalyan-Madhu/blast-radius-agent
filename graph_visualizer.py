"""Render data/topology.json as an interactive pyvis graph with blast-radius coloring."""
import json
import sys
from pathlib import Path

import networkx as nx
from pyvis.network import Network

TOPOLOGY_PATH = Path(__file__).with_name("data") / "topology.json"
OUTPUT_PATH = Path(__file__).with_name("topology_graph.html")

HEALTHY = "#2ECC71"
FAILING = "#E74C3C"
AT_RISK = "#F39C12"


def load_topology(path=TOPOLOGY_PATH):
    """Directed graph where an edge source -> target means source calls (depends on) target."""
    topo = json.loads(Path(path).read_text(encoding="utf-8"))
    graph = nx.DiGraph()
    for svc in topo["services"]:
        graph.add_node(svc["id"], **svc)
    for edge in topo["edges"]:
        graph.add_edge(edge["source"], edge["target"], protocol=edge["protocol"], mode=edge["mode"])
    return graph


def blast_radius(graph, failing):
    """Services exposed to a failure: everything that transitively calls a failing service."""
    exposed = set().union(*(nx.ancestors(graph, f) for f in failing)) if failing else set()
    return exposed - set(failing)


def node_color(node, failing, at_risk):
    if node in failing:
        return FAILING
    if node in at_risk:
        return AT_RISK
    return HEALTHY


def render_topology(failing=(), at_risk=None, output=OUTPUT_PATH, graph=None):
    """Write the interactive HTML graph and return its path.

    failing: services that are down (red).
    at_risk: services predicted to be impacted (orange). Defaults to the computed blast radius.
    """
    graph = graph if graph is not None else load_topology()
    failing = set(failing)
    at_risk = blast_radius(graph, failing) if at_risk is None else set(at_risk) - failing

    net = Network(height="600px", width="100%", directed=True, bgcolor="#1E1E1E", font_color="#FFFFFF",
                  cdn_resources="remote")  # remote = single self-contained file, embeddable in Streamlit
    for node, data in graph.nodes(data=True):
        status = "FAILING" if node in failing else "AT RISK" if node in at_risk else "healthy"
        net.add_node(
            node,
            label=node,
            color=node_color(node, failing, at_risk),
            size=32 if node in failing else 24,
            shape="dot",
            title=f"{node} [{status}]\n{data['runtime']} | {data['replicas']} replicas\n"
                  f"{data['criticality']} | owner: {data['owner']}",
        )
    for source, target, data in graph.edges(data=True):
        net.add_edge(source, target, title=f"{source} calls {target} ({data['protocol']}, {data['mode']})",
                     color="#888888", arrows="to")
    net.set_options('{"physics": {"barnesHut": {"springLength": 180}, "stabilization": {"iterations": 200}}}')

    output = Path(output)
    output.write_text(net.generate_html(), encoding="utf-8")
    return output


if __name__ == "__main__":
    g = load_topology()
    assert blast_radius(g, {"token-refresh"}) == {"auth-service", "payment-service", "api-gateway"}
    assert blast_radius(g, {"user-db"}) == set(g.nodes) - {"user-db"}
    assert blast_radius(g, {"api-gateway"}) == set()

    failing = sys.argv[1:]  # e.g. python graph_visualizer.py user-db
    unknown = set(failing) - set(g.nodes)
    if unknown:
        sys.exit(f"Unknown service(s): {', '.join(unknown)}. Choose from: {', '.join(g.nodes)}")
    path = render_topology(failing, graph=g)
    print(f"Wrote {path} (failing: {failing or 'none'}, at risk: {sorted(blast_radius(g, set(failing))) or 'none'})")

from __future__ import annotations

import math
import time
from copy import deepcopy

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from chord_sim import ChordNetwork


st.set_page_config(page_title="Chord Lookup Simulator", layout="wide")


def build_network(node_count: int, m_bits: int, hop_latency: float) -> ChordNetwork:
    return ChordNetwork.evenly_spaced(node_count=node_count, m_bits=m_bits, hop_latency=hop_latency)


def plot_ring(network: ChordNetwork, highlight_path: list[int] | None = None):
    node_ids = network.sorted_node_ids()
    fig, ax = plt.subplots(figsize=(7, 7))
    radius = 1.0
    positions = {}

    for index, node_id in enumerate(node_ids):
        angle = 2 * math.pi * index / len(node_ids)
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        positions[node_id] = (x, y)

    circle = plt.Circle((0, 0), radius, fill=False, linestyle="--", color="#8c8c8c")
    ax.add_patch(circle)

    highlight_path = highlight_path or []
    highlight_edges = set(zip(highlight_path, highlight_path[1:]))

    for source, target in network.ring_edges():
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        color = "#d62728" if (source, target) in highlight_edges else "#9ecae1"
        linewidth = 3 if (source, target) in highlight_edges else 1.5
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops=dict(arrowstyle="->", lw=linewidth, color=color, shrinkA=18, shrinkB=18),
        )

    for node_id, (x, y) in positions.items():
        active = node_id in highlight_path
        ax.scatter(
            x,
            y,
            s=420 if active else 320,
            color="#ff7f0e" if active else "#1f77b4",
            edgecolor="white",
            linewidth=2,
            zorder=5,
        )
        ax.text(x, y, str(node_id), ha="center", va="center", color="white", fontsize=11, weight="bold")

    ax.set_title("Chord Ring Topology")
    ax.set_aspect("equal")
    ax.axis("off")
    return fig


def animate_lookup(network: ChordNetwork, result, placeholder):
    for step in range(1, len(result.path) + 1):
        with placeholder.container():
            st.pyplot(plot_ring(network, highlight_path=result.path[:step]), clear_figure=True)
            st.caption(f"Step {step}/{len(result.path)}: visited {result.path[:step]}")
        time.sleep(0.6)


def build_churn_events(node_count: int, keyspace_size: int):
    join_candidate = (node_count * 3 + 5) % keyspace_size
    return [
        {"time": 0.8, "action": "join", "node_id": join_candidate},
        {"time": 1.6, "action": "leave", "node_id": 0},
    ]


st.title("Discrete-Event Simulation of the Chord Lookup Protocol")
st.write(
    "SimPy models message delay hop-by-hop, while Streamlit visualizes the ring, finger tables, "
    "and the path taken to resolve a key lookup in a Chord DHT."
)

with st.sidebar:
    st.header("Simulation Controls")
    m_bits = st.slider("Identifier space bits (m)", min_value=4, max_value=8, value=6)
    max_nodes = min(2**m_bits, 64)
    node_count = st.slider("Number of active nodes", min_value=4, max_value=max_nodes, value=min(16, max_nodes), step=1)
    hop_latency = st.slider("Latency per hop", min_value=0.2, max_value=3.0, value=1.0, step=0.1)
    churn_enabled = st.toggle("Simulate joins/departures during lookup", value=False)
    animate = st.toggle("Animate message hops", value=True)

network = build_network(node_count=node_count, m_bits=m_bits, hop_latency=hop_latency)
node_ids = network.sorted_node_ids()

col1, col2 = st.columns([1.2, 1])
with col1:
    selected_node = st.selectbox("Inspect node", options=node_ids, index=0)
with col2:
    lookup_key = st.slider("Lookup key", min_value=0, max_value=network.keyspace_size - 1, value=min(11, network.keyspace_size - 1))

start_node = selected_node
baseline_result = network.simulate_lookup(start_node=start_node, key=lookup_key)
churn_events = build_churn_events(node_count=node_count, keyspace_size=network.keyspace_size)
churn_network = deepcopy(network)
churn_result = churn_network.simulate_lookup_with_churn(start_node=start_node, key=lookup_key, churn_events=churn_events)
active_result = churn_result if churn_enabled else baseline_result

summary1, summary2, summary3, summary4 = st.columns(4)
summary1.metric("Start node", start_node)
summary2.metric("Key owner", active_result.owner_node)
summary3.metric("Hop count", active_result.hop_count)
summary4.metric("Latency", f"{active_result.latency:.2f}")

topology_col, table_col = st.columns([1.4, 1])
with topology_col:
    topology_placeholder = st.empty()
    if animate:
        animate_lookup(churn_network if churn_enabled else network, active_result, topology_placeholder)
    else:
        topology_placeholder.pyplot(
            plot_ring(churn_network if churn_enabled else network, highlight_path=active_result.path),
            clear_figure=True,
        )

with table_col:
    st.subheader(f"Finger Table for Node {selected_node}")
    st.dataframe(pd.DataFrame(network.finger_table_rows(selected_node)), use_container_width=True, hide_index=True)
    st.subheader("Lookup Path")
    st.write(" -> ".join(map(str, active_result.path)))
    st.dataframe(pd.DataFrame(active_result.events), use_container_width=True, hide_index=True)

if churn_enabled:
    st.subheader("Join/Departure Events")
    st.dataframe(pd.DataFrame(churn_events), use_container_width=True, hide_index=True)
    st.caption("A short stabilization delay is injected after each churn event before routing continues.")

st.subheader("Chord Scaling Experiment")
benchmark_rows = pd.DataFrame(network.benchmark_scaling(lookup_count=32))
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(benchmark_rows["nodes"], benchmark_rows["avg_hops"], marker="o", linewidth=2, label="Average lookup hops")
ax.plot(benchmark_rows["nodes"], benchmark_rows["log2_nodes"], linestyle="--", linewidth=2, label="log2(N)")
ax.set_xlabel("Number of nodes")
ax.set_ylabel("Hops")
ax.set_title("Lookup Hop Count Grows Close to O(log N)")
ax.grid(alpha=0.3)
ax.legend()
st.pyplot(fig, clear_figure=True)
st.dataframe(benchmark_rows, use_container_width=True, hide_index=True)

st.subheader("How To Use This Demo")
st.markdown(
    """
1. Pick a ring size and a key.
2. Inspect the selected node's finger table.
3. Compare the animated route with and without churn.
4. Observe the scaling plot to see the logarithmic lookup trend as `N` grows.
"""
)

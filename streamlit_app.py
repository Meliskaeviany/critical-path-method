import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="AOA CPM", layout="wide")
st.title("Diagram AOA (Theory Style) dengan Dummy")

def load_data(uploaded_file):
    return pd.read_csv(uploaded_file)

def build_aoa_graph(data):
    G = nx.DiGraph()
    activity_map = {}
    event_counter = 1
    G.add_node(f"E{event_counter}")

    for _, row in data.iterrows():
        act = row['Notasi']
        dur = row['Durasi (Hari)']
        preds = [p.strip() for p in str(row['Kegiatan Yang Mendahului']).split(',') if p.strip() not in ('', '-')]
        if not preds:
            start = "E1"
        else:
            pred_events = [activity_map[p][1] for p in preds if p in activity_map]
            if len(set(pred_events)) == 1:
                start = pred_events[0]
            else:
                event_counter += 1
                start = f"E{event_counter}"
                for pe in set(pred_events):
                    G.add_edge(pe, start, label=f"dummy_{pe}_{start}", duration=0)
        event_counter += 1
        end = f"E{event_counter}"
        G.add_edge(start, end, label=act, duration=dur)
        activity_map[act] = (start, end)
    return G

def calculate_times(G):
    for n in G.nodes:
        G.nodes[n]['ES'] = 0
        G.nodes[n]['LF'] = float('inf')
    for n in nx.topological_sort(G):
        G.nodes[n]['ES'] = max([G.nodes[p]['ES'] + G.edges[p, n]['duration'] for p in G.predecessors(n)], default=0)
    proj_dur = max(G.nodes[n]['ES'] for n in G.nodes)
    for n in reversed(list(nx.topological_sort(G))):
        G.nodes[n]['LF'] = min([G.nodes[s]['LF'] - G.edges[n, s]['duration'] for s in G.successors(n)], default=proj_dur)
    edges = []
    for u, v, d in G.edges(data=True):
        es = G.nodes[u]['ES']
        ef = es + d['duration']
        lf = G.nodes[v]['LF']
        ls = lf - d['duration']
        slack = ls - es
        edges.append({'u': u, 'v': v, 'label': d['label'], 'dur': d['duration'], 'slack': slack})
    return G, edges, proj_dur

def layout_theory(G, edges):
    # Tentukan posisi event (node) di sumbu x = ES
    pos = {}
    # group nodes by ES value
    nodes_by_es = {}
    for n in G.nodes:
        es = G.nodes[n]['ES']
        nodes_by_es.setdefault(es, []).append(n)
    # sort unique ES
    sorted_es = sorted(nodes_by_es.keys())
    # x spacing
    x_scale = 3.0
    y_gap = 2.0
    for i, es in enumerate(sorted_es):
        xs = i * x_scale
        ys_list = nodes_by_es[es]
        # beri distribusi y agar node tidak semuanya di y = 0
        for j, n in enumerate(ys_list):
            pos[n] = (xs, j * y_gap - (len(ys_list)-1)*y_gap/2)
    return pos

def draw_diagram(G, edges, proj_dur):
    pos = layout_theory(G, edges)
    plt.figure(figsize=(12, 6))
    # draw nodes
    nx.draw_networkx_nodes(G, pos, node_size=800, node_color='lightgray')
    nx.draw_networkx_labels(G, pos, font_size=10)
    # draw edges
    for e in edges:
        u, v = e['u'], e['v']
        dur = e['dur']
        lbl = e['label']
        slack = e['slack']
        is_dummy = lbl.startswith("dummy")
        is_critical = (slack == 0 and not is_dummy)
        # choose style
        style = 'dashed' if is_dummy else 'solid'
        color = 'black' if is_dummy else ('red' if is_critical else 'blue')
        width = 1.0 if is_dummy else (2.5 if is_critical else 1.8)
        # draw arrow: proportion panjang relatif durasi
        # we will draw a straight arrow, but label with duration
        nx.draw_networkx_edges(
            G, pos, edgelist=[(u, v)], style=style, edge_color=color,
            width=width, arrows=True, arrowsize=15,
        )
        # place label (activity + durasi) at mid point
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        xm, ym = (x1 + x2)/2, (y1 + y2)/2
        plt.text(xm, ym + 0.2, f"{lbl}({dur})", fontsize=9, ha='center')
    plt.title(f"Diagram AOA (Theory Style) — Durasi Total = {proj_dur}")
    plt.axis('off')
    st.pyplot(plt)

# Streamlit app
uploaded = st.sidebar.file_uploader("CSV", type=["csv"])
if uploaded:
    df = load_data(uploaded)
    st.dataframe(df)
    G, edges, pdur = calculate_times(build_aoa_graph(df))
    draw_diagram(G, edges, pdur)
else:
    st.info("Upload file CSV")

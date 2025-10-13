import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import streamlit as st

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(
    page_title="CPM - Activity on Arrow (AOA)",
    page_icon="📈",
    layout="wide",
)
st.title("📈 CPM - Activity on Arrow (AOA) dengan Dummy & Perhitungan Lengkap")

# --- Fungsi Membaca File CSV ---
def load_data(uploaded_file):
    return pd.read_csv(uploaded_file)

# --- Bangun Jaringan AOA ---
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

# --- Hitung ES, EF, LS, LF, Slack ---
def calculate_times(G):
    for n in G.nodes:
        G.nodes[n]['ES'] = 0
        G.nodes[n]['LF'] = float('inf')

    # Forward Pass
    for n in nx.topological_sort(G):
        G.nodes[n]['ES'] = max([G.nodes[p]['ES'] + G.edges[p, n]['duration'] for p in G.predecessors(n)], default=0)

    project_duration = max(G.nodes[n]['ES'] for n in G.nodes)

    # Backward Pass
    for n in reversed(list(nx.topological_sort(G))):
        G.nodes[n]['LF'] = min([G.nodes[s]['LF'] - G.edges[n, s]['duration'] for s in G.successors(n)], default=project_duration)

    # Simpan hasil aktivitas
    edges = []
    for u, v, d in G.edges(data=True):
        es = G.nodes[u]['ES']
        ef = es + d['duration']
        lf = G.nodes[v]['LF']
        ls = lf - d['duration']
        slack = ls - es
        edges.append({
            'Dari Event': u,
            'Ke Event': v,
            'Aktivitas': d['label'],
            'Durasi': d['duration'],
            'ES': es,
            'EF': ef,
            'LS': ls,
            'LF': lf,
            'Slack': slack
        })

    df_result = pd.DataFrame(edges)
    return G, df_result, project_duration

# --- Layout Teoritis Horizontal ---
def layout_theory(G):
    pos = {}
    nodes = list(nx.topological_sort(G))
    spacing_x = 4.0
    for i, node in enumerate(nodes):
        pos[node] = (i * spacing_x, 0)
    return pos

# --- Gambar Diagram AOA ---
def draw_diagram(G, df_result, project_duration):
    pos = layout_theory(G)
    plt.figure(figsize=(15, 6))
    nx.draw_networkx_nodes(G, pos, node_size=1000, node_color='lightgray')
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')

    for _, row in df_result.iterrows():
        u, v = row['Dari Event'], row['Ke Event']
        dur = row['Durasi']
        lbl = row['Aktivitas']
        slack = row['Slack']
        is_dummy = lbl.startswith("dummy")
        is_critical = (slack == 0 and not is_dummy)

        style = 'dashed' if is_dummy else 'solid'
        color = 'black' if is_dummy else ('red' if is_critical else 'skyblue')
        width = 1 if i

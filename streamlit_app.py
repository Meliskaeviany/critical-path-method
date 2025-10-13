import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="Diagram AOA Mirip Contoh", layout="wide")
st.title("Diagram AOA Mirip Contoh dengan Dummy")

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
        G.add_node(start)
        G.add_node(end)
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
    # Posisi node berdasarkan ES tapi atur vertikal agar tidak tumpang tindih
    pos = {}
    nodes_by_es = {}
    for n in G.nodes:
        es = G.nodes[n]['ES']
        nodes_by_es.setdefault(es, []).append(n)

    sorted_es = sorted(nodes_by_es.keys())
    x_scale = 3.0  # horizontal jarak antar level
    y_gap = 2.0    # jarak antar node di vertikal

    for i, es in enumerate(sorted_es):
        xs = i * x_scale
        ys_list = nodes_by_es[es]
        for j, n in enumerate(ys_list):
            # atur agar node tidak saling tumpang tindih di vertikal
            pos[n] = (xs, j * y_gap - (len(ys_list)-1)*y_gap/2)
    return pos

def draw_node_with_divided_circle(ax, pos, node, ES, LF):
    x, y = pos[node]
    radius = 0.5
    # circle
    circle = plt.Circle((x, y), radius, edgecolor='black', facecolor='white', linewidth=2)
    ax.add_patch(circle)

    # garis vertikal tengah lingkaran
    ax.plot([x, x], [y - radius, y + radius], color='black', linewidth=1.5)

    # teks ES kiri bawah
    ax.text(x - radius/2, y - 0.3, str(int(ES)), fontsize=10, ha='center', va='center')
    # teks LF kiri atas
    ax.text(x - radius/2, y + 0.3, str(int(LF)), fontsize=10, ha='center', va='center')

    # node nomor (misal E1 -> 1 saja) di tengah kanan lingkaran
    # ambil angka dari nama node E1 -> 1
    node_num = node[1:]
    ax.text(x + radius/2, y, node_num, fontsize=12, ha='center', va='center', fontweight='bold')

def draw_diagram(G, edges, proj_dur):
    pos = layout_theory(G, edges)
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_aspect('equal')
    ax.axis('off')

    # gambar edge dulu supaya node di atas
    for e in edges:
        u, v = e['u'], e['v']
        dur = e['dur']
        lbl = e['label']
        slack = e['slack']
        is_dummy = lbl.startswith("dummy")
        is_critical = (slack == 0 and not is_dummy)

        style = 'dashed' if is_dummy else 'solid'
        color = 'black' if is_dummy else ('red' if is_critical else 'blue')
        width = 1.0 if is_dummy else (2.5 if is_critical else 1.8)

        x1, y1 = pos[u]
        x2, y2 = pos[v]

        # Draw arrow line
        ax.annotate(
            '', xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle='->', color=color, linewidth=width, linestyle=style)
        )

        # label kegiatan dan durasi di tengah panah
        xm, ym = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(xm, ym + 0.15, f"{lbl}({dur})", fontsize=10, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.7))

    # gambar node
    for n in G.nodes:
        ES = G.nodes[n]['ES']
        LF = G.nodes[n]['LF']
        draw_node_with_divided_circle(ax, pos, n, ES, LF)

    plt.title(f"Diagram AOA mirip contoh — Total Durasi = {proj_dur} hari", fontsize=16)
    st.pyplot(fig)

# Streamlit app
uploaded = st.sidebar.file_uploader("Upload CSV Data Kegiatan", type=["csv"])
if uploaded:
    df = load_data(uploaded)
    st.dataframe(df)
    G = build_aoa_graph(df)
    G, edges, proj_dur = calculate_times(G)
    draw_diagram(G, edges, proj_dur)
else:
    st.info("Upload file CSV terlebih dahulu.")

import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

st.title("Diagram AOA seperti Contoh")

def load_data(uploaded_file):
    return pd.read_csv(uploaded_file)

def build_aoa_graph(data):
    G = nx.DiGraph()
    activity_map = {}
    event_num = 1
    G.add_node(event_num)  # start event 1

    # Simpan event nodes yang dipakai
    event_of_activity = {}

    for _, row in data.iterrows():
        act = row['Notasi']
        dur = int(row['Durasi (Hari)'])
        preds = row['Kegiatan Yang Mendahului']
        if pd.isna(preds) or preds.strip() == "-" or preds.strip() == "":
            preds = []
        else:
            preds = [p.strip() for p in preds.split(',')]

        # Tentukan start event
        if len(preds) == 0:
            start_event = 1
        elif len(preds) == 1:
            start_event = event_of_activity[preds[0]][1]
        else:
            # jika lebih dari 1 predecessor, pakai dummy event
            event_num += 1
            dummy_event = event_num
            for p in preds:
                prev_end = event_of_activity[p][1]
                G.add_edge(prev_end, dummy_event, label="dummy", duration=0, dummy=True)
            start_event = dummy_event

        event_num += 1
        end_event = event_num

        G.add_edge(start_event, end_event, label=act, duration=dur, dummy=False)
        event_of_activity[act] = (start_event, end_event)
        G.add_node(start_event)
        G.add_node(end_event)

    return G

def calculate_times(G):
    # Inisialisasi ES dan LF
    for n in G.nodes:
        G.nodes[n]['ES'] = 0
        G.nodes[n]['LF'] = float('inf')

    # Forward pass (ES)
    for n in nx.topological_sort(G):
        ES_candidates = [G.nodes[p]['ES'] + G.edges[p, n]['duration'] for p in G.predecessors(n)]
        G.nodes[n]['ES'] = max(ES_candidates) if ES_candidates else 0

    # Tentukan durasi total proyek
    total_duration = max(G.nodes[n]['ES'] for n in G.nodes)

    # Backward pass (LF)
    for n in reversed(list(nx.topological_sort(G))):
        LF_candidates = [G.nodes[s]['LF'] - G.edges[n, s]['duration'] for s in G.successors(n)]
        G.nodes[n]['LF'] = min(LF_candidates) if LF_candidates else total_duration

    # Hitung slack per edge
    edges_info = []
    for u, v, data in G.edges(data=True):
        ES = G.nodes[u]['ES']
        LF = G.nodes[v]['LF']
        dur = data['duration']
        slack = LF - (ES + dur)
        edges_info.append({'u': u, 'v': v, 'label': data['label'], 'dur': dur, 'slack': slack, 'dummy': data.get('dummy', False)})

    return G, edges_info, total_duration

def pos_custom_layout(G):
    # Manual posisi berdasarkan contoh diagram supaya mirip
    pos = {
        1: (0, 0),
        2: (1.5, 1.5),
        3: (1.5, -1.5),
        4: (3, -1.5),
        5: (3, 1.5),
        6: (4.5, -1.5),
        7: (4.5, 0),
        8: (6, 0),
    }
    # Tambahkan posisi node lain jika ada node dummy
    max_x = 6
    y_vals = [-2.5, -3.5]
    for n in G.nodes:
        if n not in pos:
            max_x += 1.5
            pos[n] = (max_x, y_vals.pop(0) if y_vals else 0)
    return pos

def draw_node(ax, pos, node, ES, LF):
    x, y = pos[node]
    radius = 0.5

    # Lingkaran
    circle = plt.Circle((x, y), radius, edgecolor='black', facecolor='white', linewidth=2)
    ax.add_patch(circle)

    # Garis vertikal pembagi lingkaran
    ax.plot([x, x], [y - radius, y + radius], color='black', linewidth=1.5)

    # Tulisan ES kiri bawah
    ax.text(x - radius/2, y - 0.25, str(int(ES)), fontsize=10, ha='center', va='center')
    # Tulisan LF kiri atas
    ax.text(x - radius/2, y + 0.25, str(int(LF)), fontsize=10, ha='center', va='center')

    # Nomor node di tengah kanan lingkaran
    ax.text(x + radius/2, y, str(node), fontsize=12, fontweight='bold', ha='center', va='center')

def draw_diagram(G, edges_info, total_duration):
    pos = pos_custom_layout(G)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_aspect('equal')
    ax.axis('off')

    # Gambar edges
    for e in edges_info:
        u, v = e['u'], e['v']
        label = e['label']
        dur = e['dur']
        slack = e['slack']
        dummy = e['dummy']

        x1, y1 = pos[u]
        x2, y2 = pos[v]

        # Warna dan style edge
        color = 'red' if slack == 0 and not dummy else 'black'
        linestyle = 'dashed' if dummy else 'solid'
        linewidth = 2 if slack == 0 and not dummy else 1.5

        # Panah edge
        ax.annotate(
            "", xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle='->', color=color, linewidth=linewidth, linestyle=linestyle)
        )

        # Label aktivitas + durasi di tengah panah
        xm, ym = (x1 + x2)/2, (y1 + y2)/2
        ax.text(xm, ym + 0.15, f"{label} ({dur})", fontsize=10, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.7))

    # Gambar node
    for n in G.nodes:
        ES = G.nodes[n]['ES']
        LF = G.nodes[n]['LF']
        draw_node(ax, pos, n, ES, LF)

    plt.title(f"Diagram AOA - Total Durasi Proyek: {total_duration} hari", fontsize=16)
    st.pyplot(fig)

uploaded = st.file_uploader("Upload CSV Data Kegiatan", type=["csv"])
if uploaded:
    df = load_data(uploaded)
    st.dataframe(df)
    G = build_aoa_graph(df)
    G, edges_info, total_duration = calculate_times(G)
    draw_diagram(G, edges_info, total_duration)
else:
    st.info("Silakan upload file CSV dengan data kegiatan.")

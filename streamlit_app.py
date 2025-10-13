import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import streamlit as st

# --- Konfigurasi halaman Streamlit ---
st.set_page_config(
    page_title="CPM (Activity on Arrow - AOA)",
    page_icon="📈",
    layout="wide",
)

st.title("📈 CPM - Activity on Arrow (AOA) Teratur dengan Dummy (Horizontal Layout)")

# --- Fungsi untuk membaca data CSV ---
def load_data(uploaded_file):
    return pd.read_csv(uploaded_file)

# --- Bangun graf AOA dengan dummy ---
def build_aoa_graph(data):
    G = nx.DiGraph()
    activity_map = {}
    event_counter = 1
    G.add_node(f"E{event_counter}")

    for _, row in data.iterrows():
        activity = row['Notasi']
        duration = row['Durasi (Hari)']
        predecessors = [
            p.strip() for p in str(row['Kegiatan Yang Mendahului']).split(',')
            if p.strip() not in ('', '-')
        ]

        if not predecessors:
            start = "E1"
        else:
            pred_events = [activity_map[p][1] for p in predecessors if p in activity_map]
            if len(set(pred_events)) == 1:
                start = pred_events[0]
            else:
                event_counter += 1
                start = f"E{event_counter}"
                for pe in set(pred_events):
                    dummy_label = f"dummy_{pe}_{start}"
                    G.add_edge(pe, start, label=dummy_label, duration=0)

        event_counter += 1
        end = f"E{event_counter}"
        G.add_edge(start, end, label=activity, duration=duration)
        activity_map[activity] = (start, end)

    return G

# --- Hitung waktu CPM (Forward & Backward Pass) ---
def calculate_aoa_times(G):
    for node in G.nodes:
        G.nodes[node]['ES'] = 0
        G.nodes[node]['LF'] = float('inf')

    # Forward pass
    for node in nx.topological_sort(G):
        es = max(
            [G.nodes[pred]['ES'] + G.edges[pred, node]['duration'] for pred in G.predecessors(node)],
            default=0
        )
        G.nodes[node]['ES'] = es

    project_duration = max(G.nodes[n]['ES'] for n in G.nodes)

    # Backward pass
    for node in reversed(list(nx.topological_sort(G))):
        lf = min(
            [G.nodes[succ]['LF'] - G.edges[node, succ]['duration'] for succ in G.successors(node)],
            default=project_duration
        )
        G.nodes[node]['LF'] = lf if lf != float('inf') else project_duration

    # Slack per aktivitas
    edge_data = []
    for u, v, d in G.edges(data=True):
        es = G.nodes[u]['ES']
        ef = es + d['duration']
        lf = G.nodes[v]['LF']
        ls = lf - d['duration']
        slack = ls - es
        edge_data.append({
            'Aktivitas': d['label'],
            'Dari Event': u,
            'Ke Event': v,
            'Durasi': d['duration'],
            'ES': es,
            'EF': ef,
            'LS': ls,
            'LF': lf,
            'Slack': slack
        })

    df_result = pd.DataFrame(edge_data)
    return G, df_result, project_duration

# --- Layout horizontal manual berdasarkan topological order ---
def horizontal_layout(G):
    layers = {}
    for i, node in enumerate(nx.topological_sort(G)):
        layers[node] = i

    pos = {}
    y_step = 2.0
    for i, node in enumerate(G.nodes()):
        x = layers[node] * 3.5  # jarak antar event horizontal
        y = 0
        pos[node] = (x, y)
    return pos

# --- Gambar grafik AOA ---
def draw_aoa(G, df_result, project_duration):
    pos = horizontal_layout(G)
    edge_labels = nx.get_edge_attributes(G, 'label')

    dummy_edges = [(u, v) for u, v, d in G.edges(data=True) if 'dummy' in d['label']]
    real_edges = [(u, v) for u, v, d in G.edges(data=True) if 'dummy' not in d['label']]
    critical_edges = [
        (row['Dari Event'], row['Ke Event'])
        for _, row in df_result[df_result['Slack'] == 0].iterrows()
        if 'dummy' not in row['Aktivitas']
    ]

    plt.figure(figsize=(18, 6))
    nx.draw_networkx_nodes(G, pos, node_color='lightgray', node_size=1200)
    nx.draw_networkx_labels(G, pos, font_size=9, font_weight='bold')

    # Aktivitas utama (biru solid)
    nx.draw_networkx_edges(G, pos, edgelist=real_edges, edge_color='skyblue',
                           width=1.8, arrows=True, arrowsize=15)
    # Dummy (hitam putus-putus kecil)
    nx.draw_networkx_edges(G, pos, edgelist=dummy_edges, edge_color='black',
                           style='dashed', width=1, arrows=True, arrowsize=8)
    # Critical path (merah tebal)
    nx.draw_networkx_edges(G, pos, edgelist=critical_edges, edge_color='red',
                           width=3, arrows=True, arrowsize=20)

    # Label aktivitas
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='black', font_size=8)

    plt.title(
        f"Diagram AOA (Activity on Arrow)\nDummy = Hitam Putus-Putus | Jalur Kritis = Merah | Total Durasi: {project_duration} Hari",
        fontsize=13, fontweight='bold'
    )
    plt.axis('off')
    st.pyplot(plt)

# --- Template CSV ---
def create_csv_template():
    data = {
        'No.': [1, 2, 3, 4, 5],
        'Aktivitas': ['Pembersihan', 'Galian Tanah', 'Urugan', 'Pondasi', 'Pengecoran'],
        'Notasi': ['A', 'B', 'C', 'D', 'E'],
        'Durasi (Hari)': [5, 3, 2, 4, 6],
        'Kegiatan Yang Mendahului': ['-', 'A', 'A', 'B,C', 'D']
    }
    return pd.DataFrame(data).to_csv(index=False)

# --- Sidebar ---
st.sidebar.header("📊 Pengaturan Input")
uploaded_file = st.sidebar.file_uploader("Upload File CSV", type=["csv"])
st.sidebar.download_button("Download Template CSV", create_csv_template(), "template_cpm_aoa.csv")

# --- Main ---
if uploaded_file is not None:
    df = load_data(uploaded_file)
    st.subheader("📋 Data Aktivitas")
    st.dataframe(df)

    try:
        G = build_aoa_graph(df)
        G, df_result, duration = calculate_aoa_times(G)
        draw_aoa(G, df_result, duration)

        st.subheader("🧮 Hasil Perhitungan CPM (AOA)")
        st.dataframe(df_result.style.format(precision=2))

        critical_activities = df_result[df_result['Slack'] == 0]['Aktivitas'].tolist()
        st.success(f"**Jalur Kritis (Critical Path):** {' → '.join(critical_activities)}")
        st.info(f"**Durasi Total Proyek:** {duration} hari")

    except Exception as e:
        st.error(f"Terjadi kesalahan saat memproses data: {e}")
else:
    st.info("📂 Silakan upload file CSV terlebih dahulu untuk memulai perhitungan.")

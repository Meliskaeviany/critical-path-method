import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import streamlit as st

# ==============================
# Konfigurasi halaman Streamlit
# ==============================
st.set_page_config(
    page_title="CPM (Critical Path Method) AOA",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================
# Fungsi baca data CSV
# ==============================
def load_data(uploaded_file):
    return pd.read_csv(uploaded_file)

# ==============================
# Fungsi utama: AOA (Activity on Arrow)
# ==============================
def calculate_cpm(data, show_dummy, dash_length, dash_gap):
    G = nx.DiGraph()

    # === AOA: Edge = Aktivitas, Node = Event ===
    for _, row in data.iterrows():
        G.add_edge(
            row['StartEvent'],
            row['EndEvent'],
            activity=row['Activity'],
            duration=row['Durasi (Hari)']
        )

    try:
        # === Forward Pass (Early Event Time) ===
        early_event = {}
        for node in nx.topological_sort(G):
            preds = list(G.predecessors(node))
            if preds:
                early_event[node] = max(early_event[p] + G[p][node]['duration'] for p in preds)
            else:
                early_event[node] = 0

        # === Backward Pass (Late Event Time) ===
        project_duration = max(early_event.values())
        late_event = {}
        for node in reversed(list(nx.topological_sort(G))):
            succs = list(G.successors(node))
            if succs:
                late_event[node] = min(late_event[s] - G[node][s]['duration'] for s in succs)
            else:
                late_event[node] = project_duration

        # === Hitung ES, EF, LS, LF, Slack tiap aktivitas ===
        for u, v, d in G.edges(data=True):
            d['ES'] = early_event[u]
            d['EF'] = d['ES'] + d['duration']
            d['LF'] = late_event[v]
            d['LS'] = d['LF'] - d['duration']
            d['Slack'] = d['LS'] - d['ES']

        # === Critical Path ===
        critical_edges = [(u, v) for u, v, d in G.edges(data=True) if d['Slack'] == 0]
        critical_activities = [G[u][v]['activity'] for u, v in critical_edges]
        critical_path_duration = project_duration

        # === Layout (tetap gaya kamu sebelumnya) ===
        for node in G.nodes:
            G.nodes[node]['level'] = early_event[node] if node in early_event else 0
        pos = nx.multipartite_layout(G, subset_key="level")

        # === Dummy edges (visualisasi) ===
        dummy_edges = []
        if show_dummy:
            sorted_nodes = sorted(G.nodes)
            for i in range(len(sorted_nodes) - 1):
                u, v = sorted_nodes[i], sorted_nodes[i + 1]
                if not G.has_edge(u, v) and not G.has_edge(v, u):
                    dummy_edges.append((u, v))

        # === Gambar grafik ===
        plt.figure(figsize=(60, 20), dpi=500)
        plt.rcParams['lines.dashed_pattern'] = [dash_length, dash_gap]

        nx.draw_networkx_edges(G, pos, edge_color='gray')
        nx.draw_networkx_nodes(G, pos, node_size=3500, node_color='skyblue')
        nx.draw_networkx_labels(G, pos, labels={n: n for n in G.nodes}, font_size=13, font_weight='bold')

        # Label edge: aktivitas + durasi
        edge_labels = {(u, v): f"{d['activity']} ({d['duration']})" for u, v, d in G.edges(data=True)}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=12)

        # Garis jalur kritis (merah)
        nx.draw_networkx_edges(G, pos, edgelist=critical_edges, edge_color='red', width=2)

        # Dummy edges (putus-putus hitam)
        if show_dummy and dummy_edges:
            nx.draw_networkx_edges(
                G, pos,
                edgelist=dummy_edges,
                style='dashed',
                edge_color='black',
                width=1.5,
                alpha=0.9,
                arrows=True,
                arrowsize=20,
                connectionstyle='arc3,rad=0'
            )

        plt.title(f'Critical Path: {" → ".join(critical_activities)}\nTotal Duration: {critical_path_duration} hari',
                  fontsize=20)
        plt.axis('off')
        st.pyplot(plt)

        # === Tampilkan tabel hasil per aktivitas ===
        data_table = []
        for u, v, d in G.edges(data=True):
            data_table.append([
                d['activity'],
                f"{u}→{v}",
                d['duration'],
                d['ES'],
                d['EF'],
                d['LS'],
                d['LF'],
                d['Slack']
            ])
        df_result = pd.DataFrame(data_table, columns=['Activity', 'From→To', 'Durasi', 'ES', 'EF', 'LS', 'LF', 'Slack'])

        st.subheader("Informasi Jalur Kritis")
        st.markdown(f"**Jalur Kritis:** {' → '.join(critical_activities)}")
        st.markdown(f"**Total Durasi Proyek:** {critical_path_duration} hari")

        st.subheader("Tabel Hasil Perhitungan CPM (AOA)")
        st.dataframe(df_result)

    except nx.NetworkXUnfeasible:
        st.error("Struktur grafik tidak valid (mungkin ada siklus atau kesalahan notasi). Silakan periksa kembali.")

# ==============================
# Sidebar (TIDAK DIUBAH)
# ==============================
st.sidebar.header('Critical Path Method (AOA)')
uploaded_file = st.sidebar.file_uploader("Upload File CSV", type=["csv"])

# ✅ Kontrol visual dummy edge
show_dummy = st.sidebar.checkbox("Tampilkan Dummy Edge Visual", value=True)

st.sidebar.markdown("### ⚙️ Pengaturan Dummy Edge")
dash_length = st.sidebar.slider("Panjang garis (px)", 2, 20, 6)
dash_gap = st.sidebar.slider("Jarak antar garis (px)", 2, 20, 4)

with st.sidebar.expander("Petunjuk :", expanded=False):
    st.markdown(
        '<p style="font-size: 10px;">Gunakan format AOA: setiap baris menunjukkan satu aktivitas di antara dua event.<br>'
        'Contoh: (1) → A → (2) → B → (3)</p>',
        unsafe_allow_html=True
    )

with st.sidebar.expander("Keterangan :", expanded=False):
    st.markdown(
        '<p style="font-size: 10px;">'
        'ES : Waktu mulai paling awal<br>'
        'EF : Waktu selesai paling awal<br>'
        'LS : Waktu mulai paling lambat<br>'
        'LF : Waktu selesai paling lambat<br>'
        'Slack : Waktu kelonggaran aktivitas<br>'
        'Dummy Edge : Edge putus-putus hitam (visualisasi AOA, tidak mempengaruhi perhitungan)</p>',
        unsafe_allow_html=True
    )

# ==============================
# Judul halaman
# ==============================
st.title("📊 Critical Path Method (AOA)")

# ==============================
# Proses utama
# ==============================
if uploaded_file is not None:
    df = load_data(uploaded_file)
    st.write("Data yang diupload:")
    st.dataframe(df)
    calculate_cpm(df, show_dummy, dash_length, dash_gap)
else:
    st.info("Silakan upload file CSV terlebih dahulu.")

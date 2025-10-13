import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

st.set_page_config(page_title="Critical Path Method - AOA", layout="wide")

st.title("📈 AOA Critical Path Method (Activity on Arrow)")

st.markdown("""
Model ini menggunakan pendekatan **AOA (Activity on Arrow)** —  
setiap aktivitas direpresentasikan sebagai **panah (arrow)** antara dua event (node).
""")

# ==============================
# Upload CSV
# ==============================
uploaded_file = st.file_uploader("📤 Upload file CSV (Format: Activity, StartEvent, EndEvent, Durasi (Hari))", type=["csv"])

show_dummy = st.checkbox("Tampilkan Dummy Edge", value=False)
dash_length = st.slider("Panjang garis putus-putus dummy", 1, 20, 5)
dash_gap = st.slider("Jarak antar garis putus-putus dummy", 1, 20, 3)


# ==============================
# Fungsi utama perhitungan CPM (AOA)
# ==============================
def calculate_cpm(data, show_dummy, dash_length, dash_gap):
    required_cols = {'Activity', 'StartEvent', 'EndEvent', 'Durasi (Hari)'}
    data_cols = set(data.columns.astype(str))

    if not required_cols.issubset(data_cols):
        missing = sorted(list(required_cols - data_cols))
        st.error(
            f"❌ Format CSV tidak sesuai untuk model AOA.\n\n"
            f"Kolom yang dibutuhkan: {', '.join(sorted(required_cols))}\n"
            f"Kolom yang ditemukan: {', '.join(sorted(data_cols))}\n"
            f"Kolom yang hilang: {', '.join(missing)}\n\n"
            "✅ Contoh format CSV yang benar:\n\n"
            "Activity,StartEvent,EndEvent,Durasi (Hari)\n"
            "A,1,2,4\n"
            "B,2,3,3\n"
            "C,1,3,5\n"
        )
        return

    # ------------------------------
    # Bangun grafik AOA (Activity on Arrow)
    # ------------------------------
    G = nx.DiGraph()

    for _, row in data.iterrows():
        start = str(row['StartEvent']).strip()
        end = str(row['EndEvent']).strip()
        activity = str(row['Activity']).strip()
        duration = float(row['Durasi (Hari)'])

        G.add_edge(start, end, activity=activity, duration=duration)

    try:
        # Forward pass
        early_event = {}
        for node in nx.topological_sort(G):
            preds = list(G.predecessors(node))
            if preds:
                early_event[node] = max(early_event[p] + G[p][node]['duration'] for p in preds)
            else:
                early_event[node] = 0

        # Backward pass
        project_duration = max(early_event.values())
        late_event = {}
        for node in reversed(list(nx.topological_sort(G))):
            succs = list(G.successors(node))
            if succs:
                late_event[node] = min(late_event[s] - G[node][s]['duration'] for s in succs)
            else:
                late_event[node] = project_duration

        # Hitung ES, EF, LS, LF, Slack untuk setiap aktivitas (edge)
        for u, v, d in G.edges(data=True):
            d['ES'] = early_event[u]
            d['EF'] = d['ES'] + d['duration']
            d['LF'] = late_event[v]
            d['LS'] = d['LF'] - d['duration']
            d['Slack'] = d['LS'] - d['ES']

        # Tentukan jalur kritis
        critical_edges = [(u, v) for u, v, d in G.edges(data=True) if d['Slack'] == 0]
        critical_activities = [G[u][v]['activity'] for u, v in critical_edges]

        # Layout AOA (urut berdasarkan nomor event)
        for node in G.nodes:
            G.nodes[node]['level'] = int(node)
        pos = nx.multipartite_layout(G, subset_key="level")

        # Dummy edge
        dummy_edges = []
        if show_dummy:
            sorted_nodes = sorted(G.nodes, key=lambda n: int(n))
            for i in range(len(sorted_nodes) - 1):
                u, v = sorted_nodes[i], sorted_nodes[i + 1]
                if not G.has_edge(u, v) and not G.has_edge(v, u):
                    dummy_edges.append((u, v))

        # ------------------------------
        # Visualisasi Grafik
        # ------------------------------
        plt.figure(figsize=(60, 20), dpi=500)
        plt.rcParams['lines.dashed_pattern'] = [dash_length, dash_gap]

        nx.draw_networkx_edges(G, pos, edge_color='gray')
        nx.draw_networkx_nodes(G, pos, node_size=3500, node_color='skyblue')
        nx.draw_networkx_labels(G, pos, labels={n: n for n in G.nodes}, font_size=13, font_weight='bold')

        edge_labels = {(u, v): f"{d['activity']} ({int(d['duration'])})" for u, v, d in G.edges(data=True)}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=12)

        nx.draw_networkx_edges(G, pos, edgelist=critical_edges, edge_color='red', width=2)

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

        plt.title(f'Critical Path: {" → ".join(critical_activities)}\nTotal Duration: {project_duration} hari', fontsize=20)
        plt.axis('off')
        st.pyplot(plt)

        # ------------------------------
        # Tabel hasil CPM
        # ------------------------------
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

        st.subheader("📊 Informasi Jalur Kritis")
        st.markdown(f"**Jalur Kritis:** {' → '.join(critical_activities)}")
        st.markdown(f"**Total Durasi Proyek:** {project_duration} hari")

        st.subheader("📋 Tabel Hasil Perhitungan CPM (AOA)")
        st.dataframe(df_result)

    except nx.NetworkXUnfeasible:
        st.error("Struktur grafik tidak valid (mungkin ada siklus atau kesalahan notasi). Silakan periksa kembali.")


# ==============================
# Jalankan jika file di-upload
# ==============================
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    calculate_cpm(df, show_dummy, dash_length, dash_gap)
else:
    st.info("📥 Silakan upload file CSV untuk menampilkan diagram AOA dan hasil perhitungan CPM.")

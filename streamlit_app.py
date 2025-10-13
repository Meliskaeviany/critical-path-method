import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import streamlit as st

# 🔧 Set konfigurasi halaman (WAJIB di awal)
st.set_page_config(
    page_title="CPM (Critical Path Method)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Fungsi untuk membaca file CSV
def load_data(uploaded_file):
    return pd.read_csv(uploaded_file)

# Fungsi utama untuk menghitung dan menampilkan CPM
def calculate_cpm(data):
    G = nx.DiGraph()
    all_nodes = set(data['Notasi'].tolist())

    # Tambahkan node ke grafik
    for _, row in data.iterrows():
        G.add_node(row['Notasi'],
                   duration=row['Durasi (Hari)'],
                   early_start=0,
                   early_finish=0,
                   late_start=float('inf'),
                   late_finish=float('inf'))

    # Tambahkan edge berdasarkan dependensi
    for _, row in data.iterrows():
        predecessors = str(row['Kegiatan Yang Mendahului']).split(',')
        for predecessor in predecessors:
            predecessor = predecessor.strip()
            if predecessor == '-' or predecessor == '':
                continue
            if predecessor in all_nodes:
                G.add_edge(predecessor, row['Notasi'])
            else:
                st.warning(f"Notasi '{predecessor}' tidak ditemukan dalam data. Dilewati. (Baris notasi: '{row['Notasi']}')")

    try:
        # === FORWARD PASS ===
        for node in nx.topological_sort(G):
            early_start = max([G.nodes[pred]['early_finish'] for pred in G.predecessors(node)], default=0)
            G.nodes[node]['early_start'] = early_start
            G.nodes[node]['early_finish'] = early_start + G.nodes[node]['duration']

        # Total durasi proyek
        project_duration = max(G.nodes[n]['early_finish'] for n in G.nodes)

        # === BACKWARD PASS ===
        for node in reversed(list(nx.topological_sort(G))):
            successors = list(G.successors(node))
            if not successors:
                G.nodes[node]['late_finish'] = project_duration
                G.nodes[node]['late_start'] = project_duration - G.nodes[node]['duration']
            else:
                min_ls = min([G.nodes[succ]['late_start'] for succ in successors])
                G.nodes[node]['late_finish'] = min_ls
                G.nodes[node]['late_start'] = min_ls - G.nodes[node]['duration']

        # Hitung slack
        for node in G.nodes:
            G.nodes[node]['Slack'] = G.nodes[node]['late_start'] - G.nodes[node]['early_start']

        # Menentukan lintasan kritis
        critical_path = [n for n in nx.topological_sort(G) if G.nodes[n]['Slack'] == 0]
        critical_path_edges = [(critical_path[i], critical_path[i + 1]) for i in range(len(critical_path) - 1)]
        critical_path_duration = project_duration

        # Visualisasi posisi
        for node in G.nodes:
            G.nodes[node]['level'] = G.nodes[node]['early_start']
        pos = nx.multipartite_layout(G, subset_key="level")

        # Label node (No, ES, LS, Durasi)
        label_full = {}
        for node in G.nodes:
            no = data[data['Notasi'] == node]['No.'].values[0]
            es = G.nodes[node]['early_start']
            ls = G.nodes[node]['late_start']
            dur = G.nodes[node]['duration']
            label_full[node] = f"{no}\nES: {es}\nLS: {ls}\nD: {dur}"

        # Gambar grafik
        plt.figure(figsize=(60, 20), dpi=500)
        nx.draw_networkx_edges(G, pos, edge_color='gray')
        nx.draw_networkx_nodes(G, pos, node_size=3500, node_color='skyblue')
        nx.draw_networkx_labels(G, pos, labels=label_full, font_size=13, font_weight='bold')
        nx.draw_networkx_edges(G, pos, edgelist=critical_path_edges, edge_color='red', width=1)

        plt.title(f'Critical Path: {" → ".join(critical_path)}\nTotal Duration: {critical_path_duration} hari', fontsize=20)
        plt.axis('off')
        st.pyplot(plt)

        # Informasi jalur kritis
        st.subheader("Informasi Jalur Kritis")
        st.markdown(f"**Jalur Kritis:** {' → '.join(critical_path)}")
        st.markdown(f"**Total Durasi Proyek:** {critical_path_duration} hari")

        # Tabel hasil CPM
        data_table = []
        for node in G.nodes:
            es = G.nodes[node]['early_start']
            ef = G.nodes[node]['early_finish']
            ls = G.nodes[node]['late_start']
            lf = G.nodes[node]['late_finish']
            slack = G.nodes[node]['Slack']
            data_table.append([node, es, ef, ls, lf, slack])
        df_result = pd.DataFrame(data_table, columns=['Node', 'ES', 'EF', 'LS', 'LF', 'Slack'])
        st.subheader("Tabel Hasil Perhitungan CPM")
        st.dataframe(df_result)

    except nx.NetworkXUnfeasible:
        st.error("Struktur grafik tidak valid (mungkin ada siklus atau kesalahan notasi). Silakan periksa kembali.")

# Template CSV
def create_csv_template():
    data = {
        'No.': [1, 2, 3, 4, 5],
        'Aktivitas': ['Pembersihan', 'Galian Tanah', 'Urugan', 'Pondasi', 'Pengecoran'],
        'Notasi': ['A', 'B', 'C', 'D', 'E'],
        'Durasi (Hari)': [5, 3, 2, 4, 6],
        'Kegiatan Yang Mendahului': ['-', 'A', 'A', 'B,C', 'D'],
    }
    df = pd.DataFrame(data)
    return df.to_csv(index=False)

# Sidebar
st.sidebar.header('Critical Path Method')
uploaded_file = st.sidebar.file_uploader("Upload Data CSV", type=["csv"])

# Tombol download template
st.sidebar.download_button("Download Template CSV", create_csv_template(), "cpm_template.csv", key="download")

# Petunjuk penggunaan
with st.sidebar.expander("Petunjuk :", expanded=False):
    st.markdown(
        '<p style="font-size: 10px;">Jika ada lebih dari 1 kegiatan yang mendahului, pisahkan dengan tanda koma (,) <br>'
        'Contoh: Untuk kegiatan D, jika kegiatan yang mendahului adalah B dan C, tuliskan sebagai B,C </p>',
        unsafe_allow_html=True
    )

with st.sidebar.expander("Keterangan :", expanded=False):
    st.markdown(
        '<p style="font-size: 10px;">' \
        'ES (Early Start)   : Waktu mulai paling awal <br>'
        'EF (Early Finish)  : Waktu selesai paling awal <br>'
        'LS (Late Start)    : Waktu mulai paling lambat <br>'
        'LF (Late Finish)   : Waktu selesai paling lambat <br>'
        'Slack / Float      : Waktu kelonggaran tanpa mengubah durasi proyek </p>',
        unsafe_allow_html=True
    )

# Judul halaman
st.title("📊 Critical Path Method")

# Proses upload dan kalkulasi
if uploaded_file is not None:
    df = load_data(uploaded_file)
    st.write("Data yang diupload:")
    st.dataframe(df)
    calculate_cpm(df)
else:
    st.info("Silakan upload file CSV terlebih dahulu.")

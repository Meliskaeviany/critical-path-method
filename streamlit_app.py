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

st.title("📈 CPM - Activity on Arrow (AOA) dengan Dummy (Hitam Putus-Putus)")

# --- Fungsi untuk membaca data CSV ---
def load_data(uploaded_file):
    return pd.read_csv(uploaded_file)

# --- Fungsi membangun graf AOA (dengan dummy) ---
def build_aoa_graph(data):
    G = nx.DiGraph()
    activity_map = {}  # simpan event start & end untuk tiap aktivitas
    event_counter = 1  # counter untuk node event (E1, E2, dst)

    # Node awal (start)
    G.add_node(f"E{event_counter}")

    for _, row in data.iterrows():
        activity = row['Notasi']
        duration = row['Durasi (Hari)']
        predecessors = [
            p.strip() for p in str(row['Kegiatan Yang Mendahului']).split(',')
            if p.strip() != '-' and p.strip() != ''
        ]

        # Jika tidak ada pendahulu → mulai dari event awal
        if not predecessors:
            start = f"E1"
        else:
            # Ambil event akhir pendahulu (atau tambahkan dummy kalau perlu)
            pred_events = [activity_map[p][1] for p in predecessors if p in activity_map]
            if len(set(pred_events)) == 1:
                start = pred_events[0]
            else:
                # Jika pendahulu berasal dari event berbeda → buat dummy untuk konvergensi
                event_counter += 1
                start = f"E{event_counter}"
                for pe in set(pred_events):
                    dummy_label = f"dummy_{pe}_{start}"
                    G.add_edge(pe, start, label=dummy_label, duration=0)

        # Buat event akhir untuk aktivitas utama
        event_counter += 1
        end = f"E{event_counter}"

        # Tambahkan edge aktivitas utama
        G.add_edge(start, end, label=activity, duration=duration)
        activity_map[activity] = (start, end)

    return G

# --- Perhitungan waktu (Forward & Backward Pass) ---
def calculate_aoa_times(G):
    # Inisialisasi waktu event
    for node in G.nodes:
        G.nodes[node]['ES'] = 0
        G.nodes[node]['LF'] = float('inf')

    # Forward Pass: Early Start setiap event
    for node in nx.topological_sort(G):
        es = max(
            [G.nodes[pred]['ES'] + G.edges[pred, node]['duration'] for pred in G.predecessors(node)],
            default=0
        )
        G.nodes[node]['ES'] = es

    project_duration = max(G.nodes[n]['ES'] for n in G.nodes)

    # Backward Pass: Late Finish setiap event
    for node in reversed(list(nx.topological_sort(G))):
        lf = min(
            [G.nodes[succ]['LF'] - G.edges[node, succ]['duration'] for succ in G.successors(node)],
            default=project_duration
        )
        G.nodes[node]['LF'] = lf if lf != float('inf') else project_duration

    # Hitung slack per aktivitas (edge)
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

# --- Gambar grafik AOA ---
def draw_aoa(G, df_result, project_duration):
    # Gunakan layout planar agar tampilan lebih rapi
    try:
        pos = nx.planar_layout(G)
    except:
        pos = nx.spring_layout(G, seed=42)

    edge_labels = nx.get_edge_attributes(G, 'label')

    # Pisahkan dummy dan aktivitas utama
    dummy_edges = [(u, v) for u, v, d in G.edges(data=True) if 'dummy' in d['label']]
    real_edges = [(u, v) for u, v, d in G.edges(data=True) if 'dummy' not in d['label']]

    plt.figure(figsize=(16, 8))
    
    # Node (event)
    nx.draw_networkx_nodes(G, pos, node_color='lightgray', node_size=1500)
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')

    # Aktivitas utama (biru solid)
    nx.draw_networkx_edges(
        G, pos, edgelist=real_edges,
        edge_color='skyblue', width=2, arrows=True, arrowsize=20
    )

    # Dummy activity (hitam putus-putus)
    nx.draw_networkx_edges(
        G, pos, edgelist=dummy_edges,
        edge_color='black', style='dashed', width=1.2, arrows=True, arrowsize=15
    )

    # Label edge
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='black', font_size=9)

    plt.title(
        f"Network Diagram - Activity on Arrow (AOA)\n"
        f"Dummy = Garis Putus-Putus Hitam | Total Durasi: {project_duration} hari",
        fontsize=14, fontweight='bold'
    )
    plt.axis('off')
    st.pyplot(plt)

# --- Template CSV untuk contoh input ---
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

with st.sidebar.expander("Petunjuk :", expanded=False):
    st.markdown("""
    - Pisahkan beberapa pendahulu dengan koma (,)
    - Gunakan '-' jika tidak ada pendahulu.
    - Dummy activity otomatis muncul untuk ketergantungan kompleks.
    """)

with st.sidebar.expander("Keterangan :", expanded=False):
    st.markdown("""
    **ES (Early Start)** : waktu mulai paling awal event  
    **EF (Early Finish)** : waktu selesai paling awal  
    **LS (Late Start)** : waktu mulai paling lambat  
    **LF (Late Finish)** : waktu selesai paling lambat  
    **Slack** : kelonggaran waktu aktivitas  
    """)

# --- Main App ---
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

import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import streamlit as st

# =======================
# 🔧 KONFIGURASI HALAMAN
# =======================
st.set_page_config(
    page_title="CPM - Activity on Arrow (AOA)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("📈 CPM - Activity on Arrow (AOA) dengan Dummy (Theory Style)")

# =======================
# 📥 BACA DATA
# =======================
def load_data(uploaded_file):
    return pd.read_csv(uploaded_file)

# =======================
# 🧩 BANGUN JARINGAN AOA
# =======================
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

# =======================
# 🧮 HITUNG WAKTU (ES, LS, DLL)
# =======================
def calculate_times(G):
    for n in G.nodes:
        G.nodes[n]['ES'] = 0
        G.nodes[n]['LF'] = float('inf')

    for n in nx.topological_sort(G):
        G.nodes[n]['ES'] = max([G.nodes[p]['ES'] + G.edges[p, n]['duration'] for p in G.predecessors(n)], default=0)

    project_duration = max(G.nodes[n]['ES'] for n in G.nodes)

    for n in reversed(list(nx.topological_sort(G))):
        G.nodes[n]['LF'] = min([G.nodes[s]['LF'] - G.edges[n, s]['duration'] for s in G.successors(n)], default=project_duration)

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
            'ES': es, 'EF': ef, 'LS': ls, 'LF': lf, 'Slack': slack
        })

    return G, pd.DataFrame(edges), project_duration

# =======================
# 🗺️ SUSUN LAYOUT TEORITIS (Jarak antar node diperkecil)
# =======================
def layout_theory(G):
    pos = {}
    nodes_by_es = {}
    for n in G.nodes:
        es = G.nodes[n]['ES']
        nodes_by_es.setdefault(es, []).append(n)
    sorted_es = sorted(nodes_by_es.keys())
    x_scale, y_gap = 2.5, 1.5  # jarak antar node diperkecil agar lebih padat
    for i, es in enumerate(sorted_es):
        x = i * x_scale
        nodes = nodes_by_es[es]
        for j, n in enumerate(nodes):
            pos[n] = (x, j * y_gap - (len(nodes)-1)*y_gap/2)
    return pos

# =======================
# 🎨 GAMBAR DIAGRAM AOA (Dummy label dihilangkan)
# =======================
def draw_aoa(G, df_result, duration):
    pos = layout_theory(G)
    plt.figure(figsize=(18, 9), facecolor='white')  # ukuran besar dan latar putih

    nx.draw_networkx_nodes(G, pos, node_size=1200, node_color='lightgray')
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')

    for _, row in df_result.iterrows():
        u, v = row['Dari Event'], row['Ke Event']
        lbl, dur, slack = row['Aktivitas'], row['Durasi'], row['Slack']
        is_dummy = lbl.startswith("dummy")
        is_critical = (slack == 0 and not is_dummy)
        style = 'dashed' if is_dummy else 'solid'
        color = 'black' if is_dummy else ('red' if is_critical else 'skyblue')
        width = 1 if is_dummy else (3 if is_critical else 2)
        nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], style=style, edge_color=color, width=width, arrows=True, arrowsize=20)
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        # Hanya tampilkan label kalau bukan dummy
        if not is_dummy:
            plt.text(
                (x1 + x2) / 2,
                (y1 + y2) / 2 + 0.3,
                f"{lbl} ({dur})",
                fontsize=11,
                ha='center',
                fontweight='bold',
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1)
            )

    plt.title(
        f"Diagram AOA (Activity on Arrow)\nDummy = Putus-Putus Hitam | Jalur Kritis = Merah | Total Durasi: {duration} hari",
        fontsize=16, fontweight='bold'
    )
    plt.axis('off')

    # Set batas sumbu agar node tidak mepet tepi
    x_vals, y_vals = zip(*pos.values())
    plt.xlim(min(x_vals) - 0.7, max(x_vals) + 0.7)
    plt.ylim(min(y_vals) - 1.5, max(y_vals) + 1.5)

    st.pyplot(plt)

# =======================
# 📄 TEMPLATE CSV
# =======================
def create_csv_template():
    data = {
        'No.': [1, 2, 3, 4, 5],
        'Aktivitas': ['Pembersihan', 'Galian Tanah', 'Urugan', 'Pondasi', 'Pengecoran'],
        'Notasi': ['A', 'B', 'C', 'D', 'E'],
        'Durasi (Hari)': [5, 3, 2, 4, 6],
        'Kegiatan Yang Mendahului': ['-', 'A', 'A', 'B,C', 'D']
    }
    return pd.DataFrame(data).to_csv(index=False)

# =======================
# 🎛️ SIDEBAR DESAIN
# =======================
st.sidebar.header("📊 Pengaturan Input")
uploaded = st.sidebar.file_uploader("Upload File CSV", type=["csv"])
st.sidebar.download_button("Download Template CSV", create_csv_template(), "template_aoa.csv")

with st.sidebar.expander("📘 Petunjuk :", expanded=False):
    st.markdown("""
    - Gunakan koma (,) untuk memisahkan beberapa pendahulu.  
    - Gunakan '-' bila tidak ada pendahulu.  
    - Dummy activity dibuat otomatis jika diperlukan.
    """)

with st.sidebar.expander("📗 Keterangan :", expanded=False):
    st.markdown("""
    **ES (Early Start)** : Waktu mulai paling awal  
    **EF (Early Finish)** : Waktu selesai paling awal  
    **LS (Late Start)** : Waktu mulai paling lambat  
    **LF (Late Finish)** : Waktu selesai paling lambat  
    **Slack** : Waktu kelonggaran aktivitas  
    """)

# =======================
# 🚀 PROSES UTAMA
# =======================
if uploaded:
    df = load_data(uploaded)
    st.subheader("📋 Data Aktivitas")
    st.dataframe(df)

    try:
        G = build_aoa_graph(df)
        G, df_result, duration = calculate_times(G)

        st.subheader("📈 Diagram AOA (Activity on Arrow)")
        draw_aoa(G, df_result, duration)

        st.subheader("🧮 Hasil Perhitungan CPM (AOA)")
        st.dataframe(df_result.style.format(precision=2))

        critical = df_result[(df_result['Slack'] == 0) & (~df_result['Aktivitas'].str.startswith('dummy'))]
        critical_path = ' → '.join(critical['Aktivitas'])
        st.success(f"**Jalur Kritis (Critical Path):** {critical_path}")
        st.info(f"**Durasi Total Proyek:** {duration} hari")

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
else:
    st.info("📂 Silakan upload file CSV untuk memulai perhitungan.")

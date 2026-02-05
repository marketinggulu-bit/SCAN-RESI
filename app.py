import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

# --- KONEKSI GSHEETS (VERSI AMAN SECRETS) ---
@st.cache_resource
def init_gsheet():
    creds_dict = st.secrets["gspread_credentials"] 
    creds = Credentials.from_service_account_info(creds_dict)
    scope = ['https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"]
    client = gspread.authorize(creds.with_scopes(scope))
    return client.open("DB_Reparasi_Produk").sheet1

# Inisialisasi koneksi global agar tidak NameError
try:
    sh = init_gsheet()
except Exception as e:
    st.error(f"Gagal koneksi GSheet: {e}")
    st.stop()

# --- INITIAL STATE ---
if 'antrean_data' not in st.session_state:
    st.session_state.antrean_data = {"Penyerahan": [], "Cetak": [], "Produksi": [], "Kirim": []}
if 'menu_aktif' not in st.session_state:
    st.session_state.menu_aktif = "Dashboard"

# --- FUNGSI UPDATE DATABASE ---
def simpan_ke_gsheet(list_resi, status_baru):
    data = sh.get_all_records()
    df = pd.DataFrame(data)
    waktu_skrg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    kolom_idx = {"Penyerahan": 3, "Cetak": 4, "Produksi": 5, "Kirim": 6}
    
    for resi in list_resi:
        resi_str = str(resi)
        if not df.empty and resi_str in df['resi_id'].astype(str).values:
            row_idx = df[df['resi_id'].astype(str) == resi_str].index[0] + 2
            sh.update_cell(row_idx, 2, status_baru)
            sh.update_cell(row_idx, kolom_idx[status_baru], waktu_skrg)
        else:
            row_data = [resi_str, status_baru, "", "", "", ""]
            row_data[kolom_idx[status_baru]-1] = waktu_skrg
            sh.append_row(row_data)

# --- UI STYLE (DARK MODE FRIENDLY) ---
st.set_page_config(page_title="Reparasi Pro", layout="centered")
st.markdown("""
    <style>
    /* Styling agar tetap nyaman di Dark Mode HP */
    .main h1, .main h2, .main h3, .main p { text-align: center !important; }
    
    /* Kartu Resi yang adaptif terhadap background */
    .resi-card {
        background-color: rgba(255, 255, 255, 0.1); 
        padding: 15px; border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        margin-bottom: 10px; text-align: center;
        font-weight: bold; color: inherit;
    }
    
    /* Mengatur tombol sidebar agar lebar penuh */
    [data-testid="stSidebar"] .stButton > button {
        width: 100%; text-align: left !important; border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR NAVIGASI ---
with st.sidebar:
    st.markdown("## 🛠️ Reparasi Pro")
    if st.button("📊 DASHBOARD UTAMA"): st.session_state.menu_aktif = "Dashboard"
    
    st.markdown("### 📥 AREA SCAN")
    for s in ["Penyerahan", "Cetak", "Produksi", "Kirim"]:
        if st.button(f"🔹 {s}"): st.session_state.menu_aktif = f"Scan {s}"
    
    st.markdown("### 🖥️ MONITORING")
    for m in ["Penyerahan", "Cetak", "Produksi"]:
        if st.button(f"📋 Monitor {m}"): st.session_state.menu_aktif = f"Mon {m}"
    
    st.markdown("---")
    if st.button("🔍 LACAK RESI"): st.session_state.menu_aktif = "Lacak"

menu = st.session_state.menu_aktif

# --- LOGIKA DASHBOARD ---
if menu == "Dashboard":
    st.markdown("# 📊 Ringkasan Produksi")
    data = sh.get_all_records()
    if data:
        df = pd.DataFrame(data)
        for stat in ["Penyerahan", "Cetak", "Produksi"]:
            st.metric(f"📦 {stat.upper()}", f"{len(df[df['status_terakhir']==stat])} resi")
    else:
        st.info("Belum ada data.")

# --- LOGIKA SCAN (OPTIMAL UNTUK BARCODE TO WEB) ---
elif "Scan" in menu:
    divisi = menu.replace("Scan ", "")
    st.markdown(f"# 🔍 Scan {divisi}")

    # Script Auto-Focus
    components.html("""
        <script>
        var input = window.parent.document.querySelector('input[data-testid="stTextInput-input"]');
        if (input) { input.focus(); }
        </script>
    """, height=0)

    # Input ini akan otomatis diisi oleh aplikasi 'Barcode to Web'
    def proses_input():
        txt = st.session_state[f"in_{divisi}"]
        if txt and txt not in st.session_state.antrean_data[divisi]:
            st.session_state.antrean_data[divisi].append(txt)
        st.session_state[f"in_{divisi}"] = ""

    st.text_input("Klik di sini (Arahkan Scanner):", key=f"in_{divisi}", on_change=proses_input)

    # List Antrean
    curr_list = st.session_state.antrean_data[divisi]
    st.markdown(f"### 📋 Antrean ({len(curr_list)})")
    for i, resi in enumerate(curr_list):
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"<div class='resi-card'>📦 {resi}</div>", unsafe_allow_html=True)
        if c2.button("🗑️", key=f"del_{i}"):
            st.session_state.antrean_data[divisi].pop(i)
            st.rerun()

    if curr_list:
        if st.button(f"🚀 KONFIRMASI {divisi.upper()}", type="primary", use_container_width=True):
            simpan_ke_gsheet(curr_list, divisi)
            st.session_state.antrean_data[divisi] = []
            st.success("Berhasil Disimpan!")
            st.rerun()

# --- LOGIKA MONITORING (LIST RAMPING) ---
elif "Mon " in menu:
    target = menu.replace("Mon ", "")
    st.markdown(f"# 🖥️ Monitor {target}")
    df = pd.DataFrame(sh.get_all_records())
    if not df.empty:
        f_df = df[df['status_terakhir'] == target].iloc[::-1]
        st.write(f"Total: **{len(f_df)} resi**")
        for _, r in f_df.iterrows():
            late = False
            if r['waktu_penyerahan']:
                diff = datetime.now() - datetime.strptime(str(r['waktu_penyerahan']), "%Y-%m-%d %H:%M:%S")
                if diff.total_seconds() > 86400: late = True
            
            with st.expander(f"{'🚨' if late else '📦'} {r['resi_id']} {'(>24 JAM!)' if late else ''}"):
                st.write(f"📥 Masuk: {r['waktu_penyerahan']}")
                st.write(f"🖨️ Cetak: {r['waktu_cetak'] or '-'}")
                st.write(f"⚒️ Produksi: {r['waktu_produksi'] or '-'}")
    else: st.info("Kosong.")

# --- LOGIKA LACAK ---
elif menu == "Lacak":
    st.markdown("# 🔍 Lacak Resi")
    cari = st.text_input("Masukkan No Barcode:")
    if cari:
        df = pd.DataFrame(sh.get_all_records())
        res = df[df['resi_id'].astype(str) == cari]
        if not res.empty:
            r = res.iloc[0]
            st.subheader(f"Status: {r['status_terakhir']}")
            for lab, val in [("📥 Penyerahan", r['waktu_penyerahan']), ("🖨️ Cetak", r['waktu_cetak']), ("⚒️ Produksi", r['waktu_produksi']), ("🚚 Kirim", r['waktu_kirim'])]:
                c1, c2 = st.columns([1, 1])
                c1.write(f"**{lab}**")
                c2.write(f": {val or '-'}")
        else: st.error("Tidak ditemukan.")

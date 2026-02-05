import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

# --- KONEKSI GSHEETS ---
@st.cache_resource
def init_gsheet():
    creds_dict = st.secrets["gspread_credentials"] 
    creds = Credentials.from_service_account_info(creds_dict)
    scope = ['https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"]
    client = gspread.authorize(creds.with_scopes(scope))
    return client.open("DB_Reparasi_Produk").sheet1

try:
    sh = init_gsheet()
except Exception as e:
    st.error(f"Koneksi GSheet Gagal: {e}")
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

# --- UI STYLE (DARK MODE & MOBILE FRIENDLY) ---
st.set_page_config(page_title="Reparasi Pro", layout="centered")
st.markdown("""
    <style>
    /* Paksa teks agar putih di mode gelap dan hitam di mode terang */
    .stApp { color: inherit; }
    
    /* Card Resi agar terlihat jelas di background gelap */
    .resi-card {
        background-color: rgba(255, 255, 255, 0.15); 
        padding: 12px; border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        margin-bottom: 8px; text-align: center;
        font-weight: bold; font-size: 1.1em;
    }
    
    /* Tombol konfirmasi agar kontras */
    .stButton > button {
        border-radius: 10px; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## 🛠️ Reparasi Pro")
    if st.button("📊 DASHBOARD UTAMA"): st.session_state.menu_aktif = "Dashboard"
    st.markdown("### 📥 AREA SCAN")
    for s in ["Penyerahan", "Cetak", "Produksi", "Kirim"]:
        if st.button(f"🔹 {s}"): st.session_state.menu_aktif = f"Scan {s}"
    st.markdown("---")
    if st.button("🔍 LACAK RESI"): st.session_state.menu_aktif = "Lacak"

menu = st.session_state.menu_aktif

# --- LOGIKA SCAN (OPTIMASI HP) ---
if "Scan" in menu:
    divisi = menu.replace("Scan ", "")
    st.markdown(f"# 🔍 Scan {divisi}")

    # Agar kursor langsung di kotak input
    components.html("""
        <script>
        var input = window.parent.document.querySelector('input[data-testid="stTextInput-input"]');
        if (input) { input.focus(); }
        </script>
    """, height=0)

    # Input Resi
    res_input = st.text_input("Arahkan Scanner Ke Sini:", key=f"in_{divisi}")

    if res_input:
        # Masukkan ke daftar jika belum ada
        if res_input not in st.session_state.antrean_data[divisi]:
            st.session_state.antrean_data[divisi].append(res_input)
            # Notifikasi kecil di HP
            st.toast(f"✅ {res_input} ditambahkan")
            # Langsung kosongkan input dengan rerun
            st.rerun()

    # Tampilkan Daftar Antrean
    curr_list = st.session_state.antrean_data[divisi]
    st.markdown(f"### 📋 Antrean ({len(curr_list)})")
    
    if curr_list:
        for i, resi in enumerate(curr_list):
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"<div class='resi-card'>📦 {resi}</div>", unsafe_allow_html=True)
            if c2.button("🗑️", key=f"del_{i}"):
                st.session_state.antrean_data[divisi].pop(i)
                st.rerun()

        # Tombol Konfirmasi
        st.write("")
        if st.button(f"🚀 KONFIRMASI {divisi.upper()}", type="primary", use_container_width=True):
            with st.spinner("Menyimpan..."):
                simpan_ke_gsheet(curr_list, divisi)
                st.session_state.antrean_data[divisi] = []
                st.success("✅ Berhasil Disimpan!")
                import time
                time.sleep(1)
                st.rerun()
    else:
        st.info("Scan barcode untuk memulai antrean.")

# --- LOGIKA DASHBOARD & LACAK TETAP SAMA ---
elif menu == "Dashboard":
    st.markdown("# 📊 Ringkasan")
    # ... (sisanya sama dengan sebelumnya)

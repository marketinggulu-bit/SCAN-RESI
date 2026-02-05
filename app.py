import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from camera_input_live import camera_input_live
from pyzbar.pyzbar import decode
import cv2
import numpy as np
# --- KONEKSI GSHEETS (VERSI AMAN SECRETS) ---
@st.cache_resource
def init_gsheet():
    # Mengambil data dari menu Secrets Streamlit
    creds_dict = st.secrets["gspread_credentials"] 
    creds = Credentials.from_service_account_info(creds_dict)
    
    scope = ['https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"]
    client = gspread.authorize(creds.with_scopes(scope))
    
    # Pastikan nama file GSheet ini sama persis di Google Drive Anda
    return client.open("DB_Reparasi_Produk").sheet1

# MENDEFINISIKAN VARIABEL 'sh' AGAR TIDAK NAMEERROR
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

# --- UI STYLE ---
st.set_page_config(page_title="Reparasi Pro", layout="centered")
st.markdown("""
    <style>
    .main h1, .main h2, .main h3, .main p, .main span { text-align: center !important; }
    .stApp {background-color: #f0f4f8;}
    [data-testid="stMetric"] {
        background: white; padding: 25px; border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.08); text-align: center;
        margin-bottom: 20px; border-bottom: 8px solid #3498db;
    }
    .resi-card {
        background: white; padding: 18px; border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 12px;
        border-top: 5px solid #FF4B4B; text-align: center; font-weight: bold;
    }
    [data-testid="stSidebar"] .stButton > button {
        width: 100%; text-align: left !important; justify-content: flex-start; border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR NAVIGASI ---
with st.sidebar:
    st.markdown("## Reparasi Pro")
    if st.button("📊 DASHBOARD UTAMA"): st.session_state.menu_aktif = "Dashboard"
    
    st.markdown("### 📥 AREA SCAN")
    if st.button("📩 Penyerahan"): st.session_state.menu_aktif = "Scan Penyerahan"
    if st.button("🖨️ Cetak"): st.session_state.menu_aktif = "Scan Cetak"
    if st.button("⚒️ Produksi"): st.session_state.menu_aktif = "Scan Produksi"
    if st.button("🚚 Kirim"): st.session_state.menu_aktif = "Scan Kirim"
    
    st.markdown("### 🖥️ MONITORING")
    if st.button("📋 Monitor Penyerahan"): st.session_state.menu_aktif = "Mon Penyerahan"
    if st.button("📋 Monitor Cetak"): st.session_state.menu_aktif = "Mon Cetak"
    if st.button("📋 Monitor Produksi"): st.session_state.menu_aktif = "Mon Produksi"
    
    st.markdown("---")
    if st.button("🔍 LACAK RESI"): st.session_state.menu_aktif = "Lacak"

menu = st.session_state.menu_aktif

# --- LOGIKA DASHBOARD ---
if menu == "Dashboard":
    st.markdown("# 📊 Ringkasan Produksi")
    st.markdown("### Pantau Status Barang Secara Real-Time")
    data = sh.get_all_records()
    if data:
        df = pd.DataFrame(data)
        st.metric("📦 PENYERAHAN", f"{len(df[df['status_terakhir']=='Penyerahan'])} resi")
        st.metric("🖨️ CETAK", f"{len(df[df['status_terakhir']=='Cetak'])} resi")
        st.metric("⚒️ PRODUKSI", f"{len(df[df['status_terakhir']=='Produksi'])} resi")
    else:
        st.info("Database kosong.")

# --- LOGIKA SCAN ---
elif "Scan" in menu:
    divisi = menu.replace("Scan ", "")
    st.markdown(f"# 🔍 Scan {divisi} (Otomatis)")

    # 1. Fitur Auto-Focus Tetap Ada untuk Scanner Fisik/Manual
    components.html(
        """<script>
        var input = window.parent.document.querySelector('input[data-testid="stTextInput-input"]');
        if (input) { input.focus(); }
        </script>""", height=0,
    )
    
    # 2. Kotak Input Manual
    val_manual = st.text_input("Ketik / Scan Manual:", key="input_resi")
    if val_manual:
        if val_manual not in st.session_state.antrean_data[divisi]:
            st.session_state.antrean_data[divisi].append(val_manual)
            st.rerun()

    # 3. Kamera Scan Otomatis
    st.write("---")
    st.caption("Arahkan kamera ke barcode untuk scan otomatis")
    image = camera_input_live(show_controls=False, key="auto_scan")

    if image:
        # Konversi gambar dari kamera ke format yang bisa dibaca OpenCV
        bytes_data = image.read()
        nparr = np.frombuffer(bytes_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Deteksi Barcode 
        barcodes = decode(img)
        
        for barcode in barcodes:
            barcode_data = barcode.data.decode('utf-8')
            if barcode_data not in st.session_state.antrean_data[divisi]:
                st.session_state.antrean_data[divisi].append(barcode_data)
                st.toast(f"✅ Terdeteksi: {barcode_data}")
                st.rerun()

    # 4. Daftar Antrean
    curr_list = st.session_state.antrean_data[divisi]
    st.markdown(f"### Daftar Antrean {divisi} ({len(curr_list)})")
    for i, resi in enumerate(curr_list):
        st.markdown(f"<div class='resi-card'>📦 RESI: {resi}</div>", unsafe_allow_html=True)
        if st.button("🗑️ Hapus", key=f"del_{divisi}_{i}"):
            st.session_state.antrean_data[divisi].pop(i)
            st.rerun()

    if curr_list:
        if st.button(f"🚀 KONFIRMASI PINDAH KE {divisi.upper()}", type="primary", use_container_width=True):
            simpan_ke_gsheet(curr_list, divisi)
            st.session_state.antrean_data[divisi] = []
            st.success("Data Berhasil Diperbarui!")
            st.rerun()

# --- LOGIKA MONITORING ---
elif "Mon " in menu:
    target = menu.replace("Mon ", "")
    st.markdown(f"# 🖥️ Monitor {target}")
    data_mon = sh.get_all_records()
    if data_mon:
        df_mon = pd.DataFrame(data_mon)
        filter_df = df_mon[df_mon['status_terakhir'] == target].copy()
        st.write(f"Total di bagian ini: **{len(filter_df)} resi**")
        st.markdown("---")
        if not filter_df.empty:
            filter_df = filter_df.iloc[::-1] 
            waktu_sekarang = datetime.now()
            for _, row in filter_df.iterrows():
                is_late = False
                label_resi = f"📦 {row['resi_id']}"
                if row['waktu_penyerahan']:
                    try:
                        waktu_awal = datetime.strptime(str(row['waktu_penyerahan']), "%Y-%m-%d %H:%M:%S")
                        if (waktu_sekarang - waktu_awal).total_seconds() > 86400:
                            is_late = True
                            label_resi = f"🚨 {row['resi_id']} (LEBIH 24 JAM!)"
                    except: pass
                with st.expander(label_resi):
                    if is_late: st.error("🚨 PERINGATAN: Mengendap > 24 jam!")
                    st.write(f"📥 Penyerahan: {row['waktu_penyerahan']}")
                    st.write(f"🖨️ Cetak: {row['waktu_cetak'] or '-'}")
                    st.write(f"⚒️ Produksi: {row['waktu_produksi'] or '-'}")
        else: st.info(f"Kosong di {target}.")

# --- LOGIKA LACAK ---
elif menu == "Lacak":
    st.markdown("# 🔍 Lacak Detail Resi")
    cari = st.text_input("Masukkan No Barcode:", key="cari_resi")
    if cari:
        data_all = sh.get_all_records()
        df_all = pd.DataFrame(data_all)
        hasil = df_all[df_all['resi_id'].astype(str) == cari]
        if not hasil.empty:
            r = hasil.iloc[0]
            st.markdown(f"### Status Saat Ini: **{r['status_terakhir']}**")
            if r['waktu_penyerahan']:
                try:
                    w_awal = datetime.strptime(str(r['waktu_penyerahan']), "%Y-%m-%d %H:%M:%S")
                    if (datetime.now() - w_awal).total_seconds() > 86400:
                        st.error("🚨 PERINGATAN: Resi ini sudah mengendap > 24 jam!")
                except: pass
            st.markdown("---")
            tahapan = [("📥 Penyerahan", r.get('waktu_penyerahan')), ("🖨️ Cetak", r.get('waktu_cetak')), ("⚒️ Produksi", r.get('waktu_produksi')), ("🚚 Kirim", r.get('waktu_kirim'))]
            for label, waktu in tahapan:
                col1, col2 = st.columns([1, 2])
                col1.write(f"**{label}**")
                col2.write(f": {waktu or '-'}")
        else: st.error("❌ Resi tidak ditemukan.")


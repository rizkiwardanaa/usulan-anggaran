import streamlit as st
import pandas as pd
import os
import sqlite3
from io import BytesIO

# ==========================================
# 1. KONFIGURASI HALAMAN, DATABASE & FOLDER
# ==========================================
st.set_page_config(page_title="Kompiler Usulan Anggaran FIB", page_icon="📝", layout="wide")

FILE_DB = "database_usulan_prodi.db"
FILE_CSV_LAMA = "database_usulan_prodi.csv" 
UPLOAD_DIR = "tor_uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def load_data():
    conn = sqlite3.connect(FILE_DB)
    cek_tabel = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table' AND name='usulan'", conn)
    
    if cek_tabel.empty:
        if os.path.exists(FILE_CSV_LAMA):
            df = pd.read_csv(FILE_CSV_LAMA)
            if "Status" not in df.columns: df["Status"] = "Menunggu Review"
            if "Catatan_Fakultas" not in df.columns: df["Catatan_Fakultas"] = "-"
            if "File_TOR" not in df.columns: df["File_TOR"] = "-"
            df.to_sql("usulan", conn, if_exists="replace", index=False)
            conn.close()
            return df
        else:
            df_kosong = pd.DataFrame(columns=[
                "Tanggal_Input", "Program_Studi", "Nama_Kegiatan", 
                "Rincian_Belanja", "Volume", "Satuan", "Harga_Satuan", 
                "Total_Usulan", "Prioritas", "Status", "Catatan_Fakultas", "File_TOR"
            ])
            df_kosong.to_sql("usulan", conn, if_exists="replace", index=False)
            conn.close()
            return df_kosong
    else:
        df = pd.read_sql("SELECT * FROM usulan", conn)
        conn.close()
        return df

def save_data(df):
    conn = sqlite3.connect(FILE_DB)
    df.to_sql("usulan", conn, if_exists="replace", index=False)
    conn.close()

df_usulan = load_data()

# ==========================================
# 2. DATABASE USER
# ==========================================
USER_CREDENTIALS = {
    "admin": {"password": "adminfib", "role": "admin", "nama_tampil": "Fakultas Ilmu Budaya (Admin)"},
    "sasindo": {"password": "123", "role": "prodi", "nama_tampil": "Sastra Indonesia"},
    "sasing": {"password": "123", "role": "prodi", "nama_tampil": "Sastra Inggris"},
    "etno": {"password": "123", "role": "prodi", "nama_tampil": "Etnomusikologi"},
    "tari": {"password": "123", "role": "prodi", "nama_tampil": "Tari"},
    "kajian": {"password": "123", "role": "prodi", "nama_tampil": "Kajian Budaya (S2)"}
}

if "logged_in" not in st.session_state:
    st.session_state.update({"logged_in": False, "role": None, "nama_user": None, "username": None})

# ==========================================
# 3. HALAMAN LOGIN
# ==========================================
if not st.session_state["logged_in"]:
    _, col_tengah, _ = st.columns([1, 2, 1])
    with col_tengah:
        st.title("🔐 Login Sistem RKA")
        st.subheader("Fakultas Ilmu Budaya - Unmul")
        with st.form("form_login"):
            u, p = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("Masuk", type="primary"):
                if u in USER_CREDENTIALS and USER_CREDENTIALS[u]["password"] == p:
                    st.session_state.update({"logged_in": True, "role": USER_CREDENTIALS[u]["role"], "nama_user": USER_CREDENTIALS[u]["nama_tampil"], "username": u})
                    st.rerun()
                else: st.error("Username atau Password salah.")
    st.stop()

# ==========================================
# 4. SIDEBAR
# ==========================================
with st.sidebar:
    st.header("Sistem Perencanaan")
    st.markdown(f"👤 **{st.session_state['nama_user']}**")
    if st.button("🚪 Logout", type="primary"):
        st.session_state.update({"logged_in": False, "role": None, "nama_user": None, "username": None})
        st.rerun()

# ==========================================
# 5A. TAMPILAN PRODI
# ==========================================
if st.session_state["role"] == "prodi":
    st.title(f"📍 Panel Usulan: {st.session_state['nama_user']}")
    tab_dash, tab_baru, tab_riwayat = st.tabs(["📊 Dashboard Prodi", "📤 Buat Usulan Baru", "📜 Monitoring & Revisi"])

    with tab_dash:
        my_data = df_usulan[df_usulan["Program_Studi"] == st.session_state["nama_user"]]
        col1, col2, col3 = st.columns(3)
        total_pengajuan = my_data["Total_Usulan"].sum()
        col1.metric("Total Anggaran Diajukan", f"Rp {total_pengajuan:,.0f}".replace(',', '.'))
        col2.metric("Jumlah Kegiatan", my_data["Nama_Kegiatan"].nunique())
        col3.metric("Usulan Disetujui", len(my_data[my_data["Status"] == "Disetujui"]["Nama_Kegiatan"].unique()))
        st.markdown("---")
        st.markdown("### 🤖 Insight & Langkah Selanjutnya")
        insights = []
        keg_tanpa_tor = my_data[my_data["File_TOR"] == "-"]["Nama_Kegiatan"].unique()
        if len(keg_tanpa_tor) > 0:
            insights.append(f"❌ **Lengkapi Dokumen:** Ada {len(keg_tanpa_tor)} kegiatan belum memiliki TOR. Upload di menu Monitoring.")
        keg_rev = my_data[my_data["Status"] == "Perlu Revisi"]["Nama_Kegiatan"].unique()
        if len(keg_rev) > 0:
            insights.append(f"⚠️ **Tindak Lanjut Revisi:** Ada {len(keg_rev)} kegiatan perlu perbaikan.")
        insights.append("ℹ️ **Saran SBM 2026:** Gunakan tarif Kalimantan Timur sesuai PMK 32/2025.")
        for item in insights: st.write(item)

    with tab_baru:
        with st.form("form_input", clear_on_submit=True):
            nama_keg = st.text_input("Nama Kegiatan Utama")
            file_tor = st.file_uploader("Upload TOR (PDF, Maks 5MB)", type=["pdf"])
            template = pd.DataFrame([{"Rincian Belanja": "", "Volume": 0, "Satuan": "Orang", "Harga Satuan": 0}])
            edited = st.data_editor(template, num_rows="dynamic", use_container_width=True, hide_index=True)
            if st.form_submit_button("Kirim Usulan"):
                valid = edited[edited["Rincian Belanja"].str.strip() != ""]
                if nama_keg and not valid.empty:
                    path_tor = "-"
                    if file_tor:
                        path_tor = os.path.join(UPLOAD_DIR, f"TOR_{st.session_state['username']}_{nama_keg[:10]}.pdf")
                        with open(path_tor, "wb") as f: f.write(file_tor.getbuffer())
                    tgl = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
                    new_data = pd.DataFrame([{
                        "Tanggal_Input": tgl, "Program_Studi": st.session_state["nama_user"], "Nama_Kegiatan": nama_keg,
                        "Rincian_Belanja": r["Rincian Belanja"], "Volume": r["Volume"], "Satuan": r["Satuan"],
                        "Harga_Satuan": r["Harga Satuan"], "Total_Usulan": r["Volume"] * r["Harga Satuan"],
                        "Prioritas": "Sedang", "Status": "Menunggu Review", "Catatan_Fakultas": "-", "File_TOR": path_tor
                    } for _, r in valid.iterrows()])
                    df_usulan = pd.concat([df_usulan, new_data], ignore_index=True)
                    save_data(df_usulan); st.success("Terkirim!"); st.rerun()

    with tab_riwayat:
        my_data = df_usulan[df_usulan["Program_Studi"] == st.session_state["nama_user"]]
        if not my_data.empty:
            sel_keg = st.selectbox("Pilih Kegiatan:", my_data["Nama_Kegiatan"].unique())
            df_curr = my_data[my_data["Nama_Kegiatan"] == sel_keg]
            st.info(f"Status: {df_curr['Status'].iloc[0]} | Catatan: {df_curr['Catatan_Fakultas'].iloc[0]}")
            st.table(df_curr[["Rincian_Belanja", "Volume", "Satuan", "Harga_Satuan", "Total_Usulan"]].style.format({"Total_Usulan": "{:,.0f}"}))

# ==========================================
# 5B. TAMPILAN ADMIN
# ==========================================
elif st.session_state["role"] == "admin":
    st.title("📊 Dashboard Monitoring & Review")
    
    if df_usulan.empty: 
        st.warning("Data kosong.")
    else:
        tab_rev, tab_hapus, tab_ins = st.tabs(["📋 Review & Analisis", "🗑️ Manajemen Data", "🤖 Insight Fakultas"])
        
        with tab_rev:
            prodi_sel = st.selectbox("Pilih Prodi:", sorted(df_usulan["Program_Studi"].unique()))
            df_p = df_usulan[df_usulan["Program_Studi"] == prodi_sel]
            for k in df_p["Nama_Kegiatan"].unique():
                df_k = df_p[df_p["Nama_Kegiatan"] == k].copy()
                with st.expander(f"{k.upper()} | Rp {df_k['Total_Usulan'].sum():,.0f} | {df_k['Status'].iloc[0]}".replace(',', '.')):
                    path = df_k["File_TOR"].iloc[0]
                    if path != "-" and os.path.exists(path):
                        with open(path, "rb") as f:
                            st.download_button("📥 Download TOR", f, file_name=os.path.basename(path), key=f"dl_{k}")
                    
                    c1, c2 = st.columns([1, 2])
                    n_s = c1.selectbox("Status:", ["Menunggu Review", "Disetujui", "Perlu Revisi", "Ditolak"], index=["Menunggu Review", "Disetujui", "Perlu Revisi", "Ditolak"].index(df_k["Status"].iloc[0]), key=f"s_{k}")
                    n_n = c2.text_area("Catatan:", value=df_k["Catatan_Fakultas"].iloc[0], key=f"n_{k}")
                    if st.button("Simpan Hasil Review", key=f"b_{k}"):
                        df_usulan.loc[(df_usulan["Program_Studi"]==prodi_sel) & (df_usulan["Nama_Kegiatan"]==k), ["Status", "Catatan_Fakultas"]] = [n_s, n_n]
                        save_data(df_usulan); st.success("Tersimpan!"); st.rerun()
                    st.dataframe(df_k[["Rincian_Belanja", "Volume", "Satuan", "Harga_Satuan", "Total_Usulan"]], hide_index=True)

            # --- FITUR DOWNLOAD EXCEL (DIKEMBALIKAN KE SINI) ---
            st.markdown("---")
            st.subheader("💾 Ekspor Data Keseluruhan")
            def to_excel(df_to_save):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_to_save.to_excel(writer, index=False, sheet_name='Rekap_Usulan')
                return output.getvalue()
            
            st.download_button(
                label="📥 Download Excel Rekapitulasi (.xlsx)",
                data=to_excel(df_usulan),
                file_name="Rekap_Usulan_FIB_2026.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with tab_hapus:
            st.subheader("🗑️ Hapus Data")
            opsi_hapus = {idx: f"[{row['Program_Studi']}] {row['Nama_Kegiatan']} - {row['Rincian_Belanja']}" for idx, row in df_usulan.iterrows()}
            sel_h = st.selectbox("Pilih:", options=list(opsi_hapus.keys()), format_func=lambda x: opsi_hapus[x])
            if st.button("🚨 Hapus Permanen", type="primary"):
                df_usulan = df_usulan.drop(index=sel_h).reset_index(drop=True)
                save_data(df_usulan); st.success("Terhapus!"); st.rerun()

        with tab_ins:
            st.subheader("🤖 Analisis Otomatis")
            tot = df_usulan['Total_Usulan'].sum()
            st.info(f"Total Usulan Masuk: **Rp {tot:,.0f}**".replace(',', '.'))
            st.bar_chart(df_usulan.groupby("Program_Studi")["Total_Usulan"].sum())

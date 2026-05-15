import streamlit as st
import pandas as pd
import os
from io import BytesIO

# ==========================================
# 1. KONFIGURASI HALAMAN & DATABASE
# ==========================================
st.set_page_config(page_title="Kompiler Usulan Anggaran FIB", page_icon="🔐", layout="wide")

FILE_DATABASE = "database_usulan_prodi.csv"

def load_data():
    if os.path.exists(FILE_DATABASE):
        df = pd.read_csv(FILE_DATABASE)
        if "Status" not in df.columns: df["Status"] = "Menunggu Review"
        if "Catatan_Fakultas" not in df.columns: df["Catatan_Fakultas"] = "-"
        return df
    else:
        return pd.DataFrame(columns=[
            "Tanggal_Input", "Program_Studi", "Nama_Kegiatan", 
            "Rincian_Belanja", "Volume", "Satuan", "Harga_Satuan", 
            "Total_Usulan", "Prioritas", "Status", "Catatan_Fakultas"
        ])

def save_data(df):
    df.to_csv(FILE_DATABASE, index=False)

df_usulan = load_data()

# ==========================================
# 2. DATABASE USER (HARDCODED)
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
                else: st.error("Username/Password salah.")
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
    tab_baru, tab_riwayat = st.tabs(["📤 Buat Usulan Baru", "📜 Monitoring & Revisi"])

    # --- TAB: INPUT BARU ---
    with tab_baru:
        with st.form("form_input", clear_on_submit=True):
            st.markdown("### 1️⃣ Informasi Utama")
            c1, c2 = st.columns([2, 1])
            nama_keg = c1.text_input("Nama Kegiatan Utama")
            prio = c2.selectbox("Prioritas", ["Tinggi", "Sedang", "Rendah"])
            
            st.markdown("### 2️⃣ Rincian RAB")
            template = pd.DataFrame([{"Rincian Belanja": "", "Volume": 0, "Satuan": "Orang", "Harga Satuan": 0}])
            edited = st.data_editor(template, num_rows="dynamic", use_container_width=True, hide_index=True, column_config={
                "Satuan": st.column_config.SelectboxColumn("Satuan", options=["Unit", "Orang", "Hari", "Bulan", "Tahun", "Jam", "Paket", "Stel", "Kegiatan"])
            })
            
            if st.form_submit_button("Kirim Usulan"):
                valid = edited[edited["Rincian Belanja"].str.strip() != ""]
                if not nama_keg.strip() or valid.empty: st.error("Lengkapi data!")
                else:
                    new_entries = []
                    tgl = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
                    for _, r in valid.iterrows():
                        new_entries.append({
                            "Tanggal_Input": tgl, "Program_Studi": st.session_state["nama_user"], "Nama_Kegiatan": nama_keg,
                            "Rincian_Belanja": r["Rincian Belanja"], "Volume": r["Volume"], "Satuan": r["Satuan"],
                            "Harga_Satuan": r["Harga Satuan"], "Total_Usulan": r["Volume"] * r["Harga Satuan"],
                            "Prioritas": prio, "Status": "Menunggu Review", "Catatan_Fakultas": "-"
                        })
                    df_usulan = pd.concat([df_usulan, pd.DataFrame(new_entries)], ignore_index=True)
                    save_data(df_usulan)
                    st.success("Usulan berhasil terkirim!"); st.rerun()

    # --- TAB: MONITORING & REVISI (TWO-WAY WORKFLOW) ---
    with tab_riwayat:
        st.markdown("### 📜 Daftar Usulan Anda")
        my_data = df_usulan[df_usulan["Program_Studi"] == st.session_state["nama_user"]]
        
        if my_data.empty: st.info("Belum ada riwayat usulan.")
        else:
            # Grouping untuk melihat daftar kegiatan unik
            my_kegiatan = my_data["Nama_Kegiatan"].unique()
            sel_keg = st.selectbox("Pilih Kegiatan untuk melihat detail/revisi:", my_kegiatan)
            
            df_curr = my_data[my_data["Nama_Kegiatan"] == sel_keg].copy()
            status_keg = df_curr["Status"].iloc[0]
            catatan_keg = df_curr["Catatan_Fakultas"].iloc[0]
            
            # Tampilan Status
            col_s1, col_s2 = st.columns(2)
            col_s1.info(f"**Status Saat Ini:** {status_keg}")
            col_s2.warning(f"**Catatan Fakultas:** {catatan_keg}")

            st.markdown("---")
            if status_keg == "Perlu Revisi":
                st.warning("⚠️ **Mode Revisi Aktif:** Anda dapat mengubah rincian di bawah ini dan mengirim ulang.")
                # Editor aktif untuk revisi
                df_to_edit = df_curr[["Rincian_Belanja", "Volume", "Satuan", "Harga_Satuan"]]
                revisi_editor = st.data_editor(df_to_edit, num_rows="dynamic", use_container_width=True, hide_index=True, key="rev_ed", column_config={
                    "Satuan": st.column_config.SelectboxColumn("Satuan", options=["Unit", "Orang", "Hari", "Bulan", "Tahun", "Jam", "Paket", "Stel", "Kegiatan"])
                })
                
                if st.button("🚀 Kirim Ulang Perbaikan"):
                    # 1. Hapus data lama kegiatan ini
                    df_usulan = df_usulan[~((df_usulan["Program_Studi"] == st.session_state["nama_user"]) & (df_usulan["Nama_Kegiatan"] == sel_keg))]
                    # 2. Masukkan data hasil revisi
                    rev_entries = []
                    tgl_rev = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
                    for _, r in revisi_editor.iterrows():
                        rev_entries.append({
                            "Tanggal_Input": tgl_rev, "Program_Studi": st.session_state["nama_user"], "Nama_Kegiatan": sel_keg,
                            "Rincian_Belanja": r["Rincian_Belanja"], "Volume": r["Volume"], "Satuan": r["Satuan"],
                            "Harga_Satuan": r["Harga_Satuan"], "Total_Usulan": r["Volume"] * r["Harga_Satuan"],
                            "Prioritas": df_curr["Prioritas"].iloc[0], "Status": "Menunggu Review", "Catatan_Fakultas": f"Revisi: {catatan_keg}"
                        })
                    df_usulan = pd.concat([df_usulan, pd.DataFrame(rev_entries)], ignore_index=True)
                    save_data(df_usulan)
                    st.success("Revisi berhasil dikirim! Status kembali menjadi Menunggu Review."); st.rerun()
            else:
                # Tampilan read-only jika tidak sedang revisi
                df_view = df_curr[["Rincian_Belanja", "Volume", "Satuan", "Harga_Satuan", "Total_Usulan"]]
                st.table(df_view.style.format({"Harga_Satuan": "{:,.0f}", "Total_Usulan": "{:,.0f}"}))

# ==========================================
# 5B. TAMPILAN ADMIN
# ==========================================
elif st.session_state["role"] == "admin":
    st.title("📊 Dashboard Monitoring & Review")
    if df_usulan.empty: st.warning("Data kosong.")
    else:
        tab1, tab2, tab3 = st.tabs(["📋 Review & Analisis", "🗑️ Manajemen Data", "🤖 Insight"])
        with tab1:
            prodi_sel = st.selectbox("Pilih Prodi:", sorted(df_usulan["Program_Studi"].unique()))
            df_p = df_usulan[df_usulan["Program_Studi"] == prodi_sel]
            for k in df_p["Nama_Kegiatan"].unique():
                df_k = df_p[df_p["Nama_Kegiatan"] == k].copy()
                with st.expander(f"{k.upper()} | Rp {df_k['Total_Usulan'].sum():,.0f} | Status: {df_k['Status'].iloc[0]}"):
                    c_st, c_nt = st.columns([1, 2])
                    n_stat = c_st.selectbox("Status:", ["Menunggu Review", "Disetujui", "Perlu Revisi", "Ditolak"], index=["Menunggu Review", "Disetujui", "Perlu Revisi", "Ditolak"].index(df_k["Status"].iloc[0]), key=f"s_{k}")
                    n_note = c_nt.text_area("Catatan:", value=df_k["Catatan_Fakultas"].iloc[0], key=f"n_{k}")
                    if st.button("Simpan Review", key=f"b_{k}"):
                        mask = (df_usulan["Program_Studi"] == prodi_sel) & (df_usulan["Nama_Kegiatan"] == k)
                        df_usulan.loc[mask, ["Status", "Catatan_Fakultas"]] = [n_stat, n_note]
                        save_data(df_usulan); st.success("Updated!"); st.rerun()
                    st.dataframe(df_k[["Rincian_Belanja", "Volume", "Satuan", "Harga_Satuan", "Total_Usulan"]], hide_index=True)
        # Tab 2 & 3 tetap sama seperti sebelumnya...
        with tab2:
            st.subheader("🗑️ Hapus Data")
            opsi_hapus = {idx: f"[{row['Program_Studi']}] {row['Nama_Kegiatan']} ➡️ {row['Rincian_Belanja']}" for idx, row in df_usulan.iterrows()}
            sel_h = st.selectbox("Pilih Rincian:", options=list(opsi_hapus.keys()), format_func=lambda x: opsi_hapus[x])
            if st.button("🚨 Hapus Permanen", type="primary"):
                df_usulan = df_usulan.drop(index=sel_h).reset_index(drop=True)
                save_data(df_usulan); st.success("Terhapus!"); st.rerun()
        with tab3:
            st.info(f"Total Usulan: Rp {df_usulan['Total_Usulan'].sum():,.0f}".replace(',', '.'))
            st.bar_chart(df_usulan.groupby("Program_Studi")["Total_Usulan"].sum())

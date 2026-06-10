import streamlit as st
import pandas as pd
from utils import engine, save_table, init_users_table, log_audit

st.title("👥 Manajemen Pengguna & Hak Akses")
st.caption("Panel eksklusif Super Admin untuk mengatur kredensial login dan menu navigasi.")

df_users = init_users_table()

# PEMECAHAN HAK AKSES HINGGA LEVEL TAB SPESIFIK
MENU_OPTIONS = {
    "kompiler": "Dashboard Usulan (Kompiler)",
    "rab_master": "RAB - 1. Master Data",
    "rab_buat": "RAB - 2. Buat / Edit RAB",
    "rab_arsip": "RAB - 3. Arsip & Versi",
    "rab_rkakl": "RAB - 4. Rekap RKAKL",
    "rab_matrik": "RAB - 5. Matrik Perubahan",
    "rab_warroom": "RAB - 6. Rapat Revisi (War Room)",
    "tor": "Generator TOR AI",
    "ekstrak": "Ekstraktor RKAKL PDF",
    "surat": "Pengolah Surat Otomatis",
    "users": "Panel Super Admin (Manajemen User)"
}

col_list, col_form = st.columns([1.5, 1])

with col_list:
    st.subheader("Daftar Pengguna Aktif")
    df_tampil = df_users[["Username", "Nama_Tampil", "Role"]].copy()
    st.dataframe(df_tampil, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("🗑️ Hapus Pengguna")
    hapus_user = st.selectbox("Pilih Username yang akan dihapus:", df_users["Username"].tolist())
    if st.button("Hapus Akun", type="primary"):
        if hapus_user == "admin":
            st.error("Akun Super Admin utama tidak boleh dihapus!")
        else:
            df_users = df_users[df_users["Username"] != hapus_user]
            save_table(df_users, "rab_users")
            log_audit("HAPUS USER", f"Menghapus akun pengguna: {hapus_user}")
            st.success(f"Akun {hapus_user} berhasil dihapus."); st.rerun()

with col_form:
    st.subheader("➕ Tambah / Edit Pengguna")
    st.info("Ketik Username yang sudah ada untuk MENGEDIT. Ketik Username baru untuk MENAMBAH.")
    
    with st.form("form_user"):
        input_uname = st.text_input("Username (Tanpa Spasi, Huruf Kecil)")
        input_pass = st.text_input("Password", type="password")
        input_nama = st.text_input("Nama Tampil (Contoh: Dekan FIB)")
        
        input_role = st.selectbox(
            "Pilih Hak Akses (Role):", 
            ["prodi", "pimpinan", "admin"],
            format_func=lambda x: "1. Prodi (Hanya Buat Usulan)" if x == "prodi" else "2. Pimpinan (Hanya Review Usulan)" if x == "pimpinan" else "3. Super Admin (Akses Sistem Penuh)"
        )
        
        akses_pilihan = st.multiselect(
            "Izinkan Akses ke Tab Berikut:",
            options=list(MENU_OPTIONS.keys()),
            format_func=lambda x: MENU_OPTIONS[x],
            default=["kompiler"] 
        )
        
        if st.form_submit_button("Simpan Data Pengguna", type="primary"):
            if not input_uname or not input_pass or not input_nama:
                st.error("Username, Password, dan Nama Tampil tidak boleh kosong!")
            elif " " in input_uname:
                st.error("Username tidak boleh mengandung spasi!")
            else:
                str_akses = ",".join(akses_pilihan)
                
                if input_uname in df_users["Username"].values:
                    df_users.loc[df_users["Username"] == input_uname, ["Password", "Role", "Nama_Tampil", "Akses_Menu"]] = [input_pass, input_role, input_nama, str_akses]
                    pesan_log = "Mengubah data kredensial"
                else:
                    new_user = pd.DataFrame([{
                        "Username": input_uname, "Password": input_pass, 
                        "Role": input_role, "Nama_Tampil": input_nama, 
                        "Akses_Menu": str_akses
                    }])
                    df_users = pd.concat([df_users, new_user], ignore_index=True)
                    pesan_log = "Membuat akun baru"
                
                save_table(df_users, "rab_users")
                log_audit("MANAJEMEN USER", f"{pesan_log} untuk username: {input_uname}")
                st.success(f"Berhasil menyimpan akun {input_uname}!"); st.rerun()

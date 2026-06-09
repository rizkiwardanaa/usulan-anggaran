import streamlit as st
from utils import authenticate_user

# ==========================================
# KONFIGURASI HALAMAN UTAMA
# ==========================================
st.set_page_config(page_title="Sistem Perencanaan FIB", page_icon="📝", layout="wide")

# Mengosongkan data keras (Hardcoded) dan menggantinya dengan session dinamis
if "logged_in" not in st.session_state:
    st.session_state.update({
        "logged_in": False, 
        "role": None, 
        "nama_user": None, 
        "username": None, 
        "akses_menu": ""
    })

# --- HALAMAN LOGIN ---
if not st.session_state["logged_in"]:
    _, col_tengah, _ = st.columns([1, 2, 1])
    with col_tengah:
        st.title("🔐 Login Sistem RKA")
        st.subheader("Fakultas Ilmu Budaya - Unmul")
        with st.form("form_login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk", type="primary"):
                # Mengecek username dan password langsung ke Database PostgreSQL
                user_data = authenticate_user(u, p)
                if user_data:
                    st.session_state.update({
                        "logged_in": True, 
                        "role": user_data["Role"], 
                        "nama_user": user_data["Nama_Tampil"], 
                        "username": user_data["Username"],
                        "akses_menu": user_data.get("Akses_Menu", "")
                    })
                    st.rerun()
                else:
                    st.error("Username atau Password salah.")
    st.stop()

# ==========================================
# NAVBAR BERJENJANG & HAK AKSES DINAMIS
# ==========================================
# 1. Mendefinisikan semua halaman yang ada
page_kompiler = st.Page("modul_utama/modul_kompiler.py", title="Dashboard Monitoring", icon="📊")

page_rab_master  = st.Page("modul_rab/rab_master.py", title="1. Master Data", icon="🗂️")
page_rab_buat    = st.Page("modul_rab/rab_buat.py", title="2. Buat / Edit RAB", icon="📝")
page_rab_arsip   = st.Page("modul_rab/rab_arsip.py", title="3. Arsip & Versi", icon="📂")
page_rab_rkakl   = st.Page("modul_rab/rab_rkakl.py", title="4. Rekap RKAKL", icon="📊")
page_rab_matrik  = st.Page("modul_rab/rab_matrik.py", title="5. Matrik Perubahan", icon="⚖️")
page_rab_warroom = st.Page("modul_rab/rab_warroom.py", title="6. Rapat Revisi", icon="🛠️")

page_tor = st.Page("modul_ekstra/modul_tor.py", title="Generator TOR", icon="🤖")
page_surat = st.Page("modul_ekstra/modul_surat.py", title="Generator Surat Otomatis", icon="✉️")
page_ekstrak = st.Page("modul_ekstra/modul_ekstrak_rkakl.py", title="Ekstrak RKAKL PDF", icon="📥")

# Halaman Khusus Super Admin
page_users = st.Page("modul_utama/manajemen_user.py", title="Manajemen Pengguna", icon="👥")

# 2. Mengatur Sidebar
with st.sidebar:
    st.header("Sistem Perencanaan")
    st.markdown(f"👤 **{st.session_state['nama_user']}**")
    st.markdown("---")
    if st.button("🚪 Logout", type="primary", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# 3. Merakit Menu Berdasarkan Hak Akses dari Database
akses_list = st.session_state["akses_menu"].split(",")
nav_dict = {}

if "kompiler" in akses_list:
    nav_dict["PAPAN KENDALI"] = [page_kompiler]
    
if "rab" in akses_list:
    nav_dict["MODUL ANGGARAN (RAB)"] = [page_rab_master, page_rab_buat, page_rab_arsip, page_rab_rkakl, page_rab_matrik, page_rab_warroom]
    
if "tor" in akses_list or "ekstrak" in akses_list:
    ekstra_pages = []
    if "tor" in akses_list: ekstra_pages.append(page_tor)
    if "ekstrak" in akses_list: ekstra_pages.append(page_ekstrak)
    if "ekstrak" in akses_list: ekstra_pages.append(page_surat)
    nav_dict["MODUL EKSTRA"] = ekstra_pages
    
if "users" in akses_list and st.session_state["role"] == "admin":
    nav_dict["PENGATURAN SUPER ADMIN"] = [page_users]

# Jika entah bagaimana user tidak punya akses apa-apa (Blank)
if not nav_dict:
    nav_dict["Akses Terbatas"] = [st.Page("modul_utama/modul_kompiler.py", title="Akses Ditolak", icon="🔒")]

pg = st.navigation(nav_dict)
pg.run()

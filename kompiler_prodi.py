import streamlit as st

st.set_page_config(page_title="Sistem Perencanaan FIB", page_icon="📝", layout="wide")

# ==========================================
# DATABASE USER & LOGIN
# ==========================================
USER_CREDENTIALS = {
    "admin": {"password": "adminfib", "role": "admin", "nama_tampil": "Fakultas Ilmu Budaya (Admin)"},
    "sasindo": {"password": "123", "role": "prodi", "nama_tampil": "Sastra Indonesia"},
    "sasing": {"password": "123", "role": "prodi", "nama_tampil": "Sastra Inggris"},
    "etno": {"password": "123", "role": "prodi", "nama_tampil": "Etnomusikologi"},
    "tari": {"password": "123", "role": "prodi", "nama_tampil": "Tari"},
    "kajian": {"password": "123", "role": "prodi", "nama_tampil": "Kajian Budaya (S2)"},
    "p2mf": {"password": "123", "role": "prodi", "nama_tampil": "Pusat Penjaminan Mutu Fakultas"}
}

if "logged_in" not in st.session_state:
    st.session_state.update({"logged_in": False, "role": None, "nama_user": None, "username": None})

if not st.session_state["logged_in"]:
    _, col_tengah, _ = st.columns([1, 2, 1])
    with col_tengah:
        st.title("🔐 Login Sistem RKA")
        st.subheader("Fakultas Ilmu Budaya - Unmul")
        with st.form("form_login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk", type="primary"):
                if u in USER_CREDENTIALS and USER_CREDENTIALS[u]["password"] == p:
                    st.session_state.update({"logged_in": True, "role": USER_CREDENTIALS[u]["role"], "nama_user": USER_CREDENTIALS[u]["nama_tampil"], "username": u})
                    st.rerun()
                else:
                    st.error("Username atau Password salah.")
    st.stop()

# ==========================================
# NAVBAR BERJENJANG DENGAN FOLDER
# ==========================================
page_kompiler = st.Page("modul_utama/modul_kompiler.py", title="Dashboard Monitoring", icon="📊")

# Pecahan RAB di dalam folder modul_rab/
page_rab_master  = st.Page("modul_rab/rab_master.py", title="1. Master Data", icon="🗂️")
page_rab_buat    = st.Page("modul_rab/rab_buat.py", title="2. Buat / Edit RAB", icon="📝")
page_rab_arsip   = st.Page("modul_rab/rab_arsip.py", title="3. Arsip & Versi", icon="📂")
page_rab_rkakl   = st.Page("modul_rab/rab_rkakl.py", title="4. Rekap RKAKL", icon="📊")
page_rab_matrik  = st.Page("modul_rab/rab_matrik.py", title="5. Matrik Perubahan", icon="⚖️")
page_rab_warroom = st.Page("modul_rab/rab_warroom.py", title="6. Rapat Revisi", icon="🛠️")

page_tor = st.Page("modul_ekstra/modul_tor.py", title="Generator TOR", icon="🤖")
page_ekstrak = st.Page("modul_ekstra/modul_ekstrak_rkakl.py", title="Ekstrak RKAKL PDF", icon="📥")

with st.sidebar:
    st.header("Sistem Perencanaan")
    st.markdown(f"👤 **{st.session_state['nama_user']}**")
    st.markdown("---")
    if st.button("🚪 Logout", type="primary", use_container_width=True):
        st.session_state.clear()
        st.rerun()

if st.session_state["role"] == "admin":
    pg = st.navigation({
        "PAPAN KENDALI": [page_kompiler],
        "MODUL ANGGARAN (RAB)": [page_rab_master, page_rab_buat, page_rab_arsip, page_rab_rkakl, page_rab_matrik, page_rab_warroom],
        "MODUL EKSTRA": [page_tor, page_ekstrak]
    })
else:
    pg = st.navigation({
        "USULAN PRODI": [page_kompiler]
    })

pg.run()

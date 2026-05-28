import streamlit as st
import pandas as pd
import re
from datetime import datetime
from sqlalchemy import create_engine
import io

try:
    import pdfplumber
except ImportError:
    st.error("⚠️ Pustaka pdfplumber belum terinstal. Pastikan file requirements.txt sudah di-update.")

# --- KONEKSI DATABASE ---
DB_URL = st.secrets["DB_URL"]
engine = create_engine(DB_URL, pool_size=5, max_overflow=10)

def load_table(table_name):
    try:
        return pd.read_sql(f"SELECT * FROM {table_name}", engine)
    except:
        return pd.DataFrame()

def save_table(df, table_name):
    with engine.connect() as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
    st.cache_data.clear()

# --- FUNGSI VERIFIKASI MATEMATIKA (V * H = T) ---
def extract_vht(text):
    tokens = text.split()
    # 1. Cari dengan rumus Vol * Harga = Total
    for i in range(len(tokens) - 2):
        t1 = tokens[i].replace(',', '').replace('.', '')
        t2 = tokens[i+1].replace(',', '').replace('.', '')
        t3 = tokens[i+2].replace(',', '').replace('.', '')
        
        if t1.isdigit() and t2.isdigit() and t3.isdigit():
            v, h, t = int(t1), int(t2), int(t3)
            if v * h == t and t > 0:
                return v, h, t, f"{tokens[i]} {tokens[i+1]} {tokens[i+2]}"
                
    # 2. Fallback: Cari 3 angka beruntun terakhir jika rumus gagal (kasus langka)
    for i in reversed(range(len(tokens) - 2)):
        t1 = tokens[i].replace(',', '').replace('.', '')
        t2 = tokens[i+1].replace(',', '').replace('.', '')
        t3 = tokens[i+2].replace(',', '').replace('.', '')
        
        if t1.isdigit() and t2.isdigit() and t3.isdigit():
            return int(t1), int(t2), int(t3), f"{tokens[i]} {tokens[i+1]} {tokens[i+2]}"
            
    return None, None, None, None

# --- MESIN PISAU PYTHON (SUPER PARSER) ---
def parse_pdf_rkakl(file_bytes):
    text = ""
    with pdfplumber.open(file_bytes) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(x_tolerance=2)
            if page_text:
                text += page_text + "\n"

    lines = text.split('\n')
    extracted_data = []
    debug_logs = []
    
    curr_keg_name = "Kegiatan Default"
    curr_akun_code = "000000"
    curr_akun_name = "Akun Tidak Dikenal"
    buffer_text = ""

    def process_buffer(b_text, keg, a_code, a_name):
        clean_text = re.sub(r'\b(BOPTN|PNBP)\b', '', b_text, flags=re.IGNORECASE).strip()
        
        # Ekstrak 3 Angka dengan Matematika Pasti
        vol, hrg, tot, matched_str = extract_vht(clean_text)
        
        if vol is None:
            debug_logs.append(f"❌ GAGAL (Tdk Ditemukan Angka): {clean_text}")
            return None
            
        # Hapus angka dari string agar Uraian bersih dari selipan angka
        clean_text = clean_text.replace(matched_str, " ")
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Pisau 1: Buang Grup
        uraian_full = clean_text
        if ":" in uraian_full:
            uraian_full = uraian_full.split(":", 1)[1].strip()

        # Pisau 2: Tarik Satuan dalam [...]
        satuan_teks = ""
        match_sat = re.search(r"\[(.*?)\]", uraian_full)
        if match_sat:
            satuan_teks = match_sat.group(1)
            uraian_full = uraian_full.replace(f"[{satuan_teks}]", "")
        else:
            match_sat_open = re.search(r"\[(.*)", uraian_full)
            if match_sat_open:
                satuan_teks = match_sat_open.group(1)
                uraian_full = uraian_full.split("[")[0]

        uraian_full = re.sub(r'\bFIB\b', '', uraian_full, flags=re.IGNORECASE).strip(" -[]")
        satuan_teks = re.sub(r'\bFIB\b', '', satuan_teks, flags=re.IGNORECASE).strip(" -[]")

        # Pisau 3: Pecah Volume x Satuan
        v1, s1, v2, s2 = vol, "Layanan", 1, "-"
        if satuan_teks:
            if " x " in satuan_teks.lower() or " X " in satuan_teks:
                parts = re.split(r"(?i)\s+x\s+", satuan_teks)
                
                p1 = parts[0].strip().split(maxsplit=1)
                if len(p1) >= 1 and p1[0].isdigit(): v1 = int(p1[0])
                if len(p1) == 2: s1 = p1[1].title()
                
                p2 = parts[1].strip().split(maxsplit=1)
                if len(p2) >= 1 and p2[0].isdigit(): v2 = int(p2[0])
                if len(p2) == 2: s2 = p2[1].title()
            else:
                p1 = satuan_teks.strip().split(maxsplit=1)
                if len(p1) >= 1 and p1[0].isdigit(): v1 = int(p1[0])
                if len(p1) == 2: s1 = p1[1].title()
                
        # Validasi akhir untuk vol total
        if v1 * v2 != vol: 
            v1 = vol # Override jika hasil kali satuan teks tidak sama dg kolom volume
            v2 = 1
            s2 = "-"

        debug_logs.append(f"✅ SUKSES: {uraian_full} || {v1} {s1} x {v2} {s2} || Rp{hrg} || Rp{tot}")
        return {
            "Kegiatan": keg, "Akun_Code": a_code, "Akun_Name": a_name,
            "Uraian": uraian_full, "Vol_1": v1, "Sat_1": s1, "Vol_2": v2, "Sat_2": s2,
            "Harga_Satuan": hrg, "Total_Biaya": tot
        }

    for line in lines:
        line = line.strip()
        if not line: continue

        match_akun = re.match(r"^(\d{6})\s+(.*)", line)
        if match_akun:
            curr_akun_code = match_akun.group(1)
            curr_akun_name = re.sub(r"[\d\.,]+\s*(BOPTN|PNBP)?$", "", match_akun.group(2)).strip()
            continue
            
        match_keg = re.match(r"^(\d{4})\s+(.*)", line)
        if match_keg:
            if not match_keg.group(2).lower().startswith("penyediaan"):
                curr_keg_name = re.sub(r"[\d\.,]+\s*$", "", match_keg.group(2)).strip()
            continue

        if line.startswith("-"):
            if buffer_text:
                res = process_buffer(buffer_text, curr_keg_name, curr_akun_code, curr_akun_name)
                if res: extracted_data.append(res)
            buffer_text = line
        elif buffer_text and not re.match(r"^(\d{6}|\d{4}|[A-Z]|\d{3})\b", line):
            buffer_text += " " + line
            
    if buffer_text:
        res = process_buffer(buffer_text, curr_keg_name, curr_akun_code, curr_akun_name)
        if res: extracted_data.append(res)

    return pd.DataFrame(extracted_data), debug_logs

# --- TAMPILAN ANTARMUKA (UI) ---
def show_page():
    st.title("📥 Mesin Ekstraksi RKAKL Otomatis")
    st.caption("Unggah PDF RKAKL dari sistem Universitas. Sistem menggunakan pdfplumber & Validasi Matematika untuk mengekstrak data.")

    if 'ekstrak_result' not in st.session_state:
        st.session_state.ekstrak_result = pd.DataFrame()
    if 'ekstrak_log' not in st.session_state:
        st.session_state.ekstrak_log = []

    with st.container(border=True):
        st.subheader("1. Setup Target Injeksi")
        col1, col2, col3 = st.columns(3)
        thn_target = col1.text_input("Tahun Anggaran", value=str(datetime.now().year + 1))
        ver_target = col2.selectbox("Versi RKA", ["Indikatif", "Definitif", "Revisi 1", "Revisi 2"])
        sumber_dana = col3.radio("Sumber Dana", ["BOPTN", "PNBP"], horizontal=True)

        file_pdf = st.file_uploader("2. Unggah Dokumen PDF RKAKL", type=['pdf'])
        
        if st.button("🚀 Ekstrak Dokumen Sekarang", type="primary"):
            if file_pdf:
                with st.spinner("Menganalisis hirarki & memverifikasi matematika teks..."):
                    df_hasil, log_debug = parse_pdf_rkakl(file_pdf)
                    st.session_state.ekstrak_log = log_debug
                    
                    if not df_hasil.empty:
                        st.session_state.ekstrak_result = df_hasil
                        st.success(f"Berhasil mengekstrak {len(df_hasil)} baris rincian belanja!")
                    else:
                        st.error("❌ Gagal mengekstrak rincian belanja. Cek Log Debug Mesin.")
            else:
                st.error("Harap unggah file PDF terlebih dahulu.")

    if st.session_state.ekstrak_log:
        with st.expander("🛠️ Log Debug Mesin (Untuk Analisis Error)"):
            for log in st.session_state.ekstrak_log:
                if log.startswith("✅"): st.success(log)
                else: st.warning(log)

    if not st.session_state.ekstrak_result.empty:
        st.markdown("---")
        st.subheader("3. Ruang Karantina (Preview Data)")
        st.info("Periksa hasil bacaan mesin di bawah ini sebelum disimpan permanen.")
        
        df_edit = st.data_editor(st.session_state.ekstrak_result, num_rows="dynamic", use_container_width=True, height=400)

        if st.button("💾 Konfirmasi & Simpan Permanen ke Database", type="primary", use_container_width=True):
            with st.spinner("Menyuntikkan data ke server..."):
                df_m_akun = load_table("rab_m_akun")
                akun_unik = df_edit[['Akun_Code', 'Akun_Name']].drop_duplicates()
                akun_baru_list = []
                for _, row in akun_unik.iterrows():
                    if df_m_akun.empty or row['Akun_Code'] not in df_m_akun['Account_Code'].values:
                        akun_baru_list.append({
                            "Sub_Komponen": "-", "Account_Code": row['Akun_Code'], 
                            "Account_Name": row['Akun_Name'], "Sumber_Dana": sumber_dana
                        })
                if akun_baru_list:
                    df_m_akun = pd.concat([df_m_akun, pd.DataFrame(akun_baru_list)], ignore_index=True)
                    save_table(df_m_akun, "rab_m_akun")
                    st.toast(f"Auto-Heal: {len(akun_baru_list)} Akun baru otomatis ditambahkan!")

                df_rab_utama = load_table("rab_utama")
                df_rab_detail = load_table("rab_detail")
                
                kegiatan_unik = df_edit['Kegiatan'].unique()
                for keg_name in kegiatan_unik:
                    new_id = f"RAB-EXT-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                    
                    df_keg_details = df_edit[df_edit['Kegiatan'] == keg_name].copy()
                    total_alokasi = df_keg_details['Total_Biaya'].sum()
                    
                    new_utama = pd.DataFrame([{
                        "ID_RAB": new_id, "Tanggal": datetime.now().strftime('%Y-%m-%d %H:%M'), 
                        "Tahun": thn_target, "Tgl_Cetak": datetime.now().strftime('%Y-%m-%d'),
                        "Sumber_Dana": sumber_dana, "KRO": "-", "RO": "-", "Komponen": "-", "Sub_Komponen": "-",
                        "Kegiatan": keg_name, "Sasaran": "-", "Volume": 1, "Satuan": "Layanan", "Alokasi": total_alokasi,
                        "Jabatan": "Dekan", "Nama_Pejabat": "-", "NIP_Pejabat": "-",
                        "Versi_RAB": ver_target, "Is_Active": 1
                    }])
                    df_rab_utama = pd.concat([df_rab_utama, new_utama], ignore_index=True)
                    
                    df_keg_details['ID_RAB'] = new_id
                    df_keg_details['Akun_Belanja'] = df_keg_details['Akun_Code'] + " - " + df_keg_details['Akun_Name']
                    new_detail = df_keg_details[['ID_RAB', 'Akun_Belanja', 'Uraian', 'Vol_1', 'Sat_1', 'Vol_2', 'Sat_2', 'Harga_Satuan', 'Total_Biaya']]
                    df_rab_detail = pd.concat([df_rab_detail, new_detail], ignore_index=True)
                
                save_table(df_rab_utama, "rab_utama")
                save_table(df_rab_detail, "rab_detail")
                
                st.session_state.ekstrak_result = pd.DataFrame() 
                st.success("🎉 Seluruh data RKAKL berhasil diinjeksi ke dalam sistem RAB Anda!")
                st.rerun()

import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from utils import load_table, get_available_years, split_kode, get_vol_sat_combined, format_rupiah, format_tgl_indo

st.title("⚖️ Matrik Perbandingan Revisi Anggaran")

list_tahun = get_available_years()
tahun_aktif = st.sidebar.selectbox("📅 Pilih Tahun Anggaran Aktif:", list_tahun)

df_rab_utama = load_table("rab_utama", ["ID_RAB", "Tanggal", "Tahun", "Tgl_Cetak", "Sumber_Dana", "KRO", "RO", "Komponen", "Sub_Komponen", "Kegiatan", "Sasaran", "Volume", "Satuan", "Alokasi", "Jabatan", "Nama_Pejabat", "NIP_Pejabat", "Versi_RAB", "Is_Active", "Catatan"], f"WHERE \"Tahun\" = '{tahun_aktif}'")

if not df_rab_utama.empty:
    ids = tuple(df_rab_utama['ID_RAB'].tolist())
    where_det = f"WHERE \"ID_RAB\" = '{ids[0]}'" if len(ids) == 1 else f"WHERE \"ID_RAB\" IN {ids}"
    df_rab_detail = load_table("rab_detail", ["ID_RAB", "Akun_Belanja", "Uraian", "Vol_1", "Sat_1", "Vol_2", "Sat_2", "Harga_Satuan", "Total_Biaya"], where_det)
else:
    df_rab_detail = pd.DataFrame(columns=["ID_RAB", "Akun_Belanja", "Uraian", "Vol_1", "Sat_1", "Vol_2", "Sat_2", "Harga_Satuan", "Total_Biaya"])

unique_kegiatans = sorted(df_rab_utama['Kegiatan'].unique()) if not df_rab_utama.empty else []
kegiatan_code_map = {keg: f"{i+1:04d}" for i, keg in enumerate(unique_kegiatans)}

def generate_matrik_html(df_matrik, v_sebelum, v_menjadi, keg_map, tahun, tgl_cetak, nama_dekan, nip_dekan, sumber_dana, tampilkan_paraf=False):
    if df_matrik.empty: return "<h3>Tidak ada data untuk dibandingkan.</h3>"
    tot_m_global_atas = df_matrik['Tot_m'].sum() if not df_matrik.empty else 0
    
    paraf_html = ""
    if tampilkan_paraf:
        paraf_html = """<table style="width: 320px; border-collapse: collapse; float: left; margin-top: 20px; font-size: 8pt;"><tr><th style="border: 1px solid black; padding: 4px;">No</th><th style="border: 1px solid black; padding: 4px;">Jabatan</th><th style="border: 1px solid black; padding: 4px;">Paraf</th></tr><tr><td style="border: 1px solid black; height: 35px; text-align: center;">1</td><td style="border: 1px solid black; padding-left: 5px;">Wakil Dekan Bidang Keuangan dan Umum</td><td style="border: 1px solid black;"></td></tr><tr><td style="border: 1px solid black; height: 35px; text-align: center;">2</td><td style="border: 1px solid black; padding-left: 5px;">Kepala Bagian Umum</td><td style="border: 1px solid black;"></td></tr><tr><td style="border: 1px solid black; height: 35px; text-align: center;">3</td><td style="border: 1px solid black; padding-left: 5px;">Staf Perencanaan</td><td style="border: 1px solid black;"></td></tr></table>"""

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>@page {{ size: A4 landscape; margin: 15mm; }} body {{ font-family: 'Arial', sans-serif; font-size: 7.5pt; line-height: 1.2; color: #000; }} .center {{ text-align: center; }} .right {{ text-align: right; }} .bold {{ font-weight: bold; }} .tabel-utama {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 7.5pt; }} .tabel-utama th, .tabel-utama td {{ border: 1px solid black; padding: 4px; vertical-align: top; }} .tabel-utama th {{ background-color: #d9d9d9; text-align: center; font-weight: bold; }} .tabel-meta {{ width: 100%; border: none; font-size: 8.5pt; margin-bottom: 10px; }} .tabel-meta td {{ padding: 2px; }} .kro-row {{ background-color: #d9e1f2; }} .ro-row {{ background-color: #e9edf4; }} .komp-row {{ background-color: #fff2cc; }} .sub-row {{ background-color: #fce4d6; }} .keg-row {{ background-color: #e2efda; }} .ttd-box {{ width: 220px; float: right; text-align: left; margin-top: 20px; margin-right: 15px; page-break-inside: avoid; }}</style></head><body>
    <h3 class="center" style="margin-bottom:2px;">MATRIK PERUBAHAN RENCANA KERJA DAN ANGGARAN</h3>
    <h4 class="center" style="margin-top:0px; margin-bottom:20px;">TAHUN ANGGARAN {tahun}<br>Versi {v_sebelum} menjadi {v_menjadi}</h4>
    <table class="tabel-meta"><tr><td width="15%" class="bold">SUMBER DANA</td><td width="2%">:</td><td class="bold">{sumber_dana}</td></tr><tr><td class="bold">ALOKASI MENJADI</td><td>:</td><td class="bold">Rp. {format_rupiah(tot_m_global_atas)}</td></tr></table>
    <table class="tabel-utama"><tr><th width="7%" rowspan="2">KODE</th><th width="30%" rowspan="2">URAIAN PROGRAM / KEGIATAN / DETAIL</th><th width="20%" colspan="3">PAGU SEMULA ({v_sebelum})</th><th width="20%" colspan="3">PAGU MENJADI ({v_menjadi})</th><th width="13%" rowspan="2">BERTAMBAH / (BERKURANG)</th></tr><tr><th>VOL</th><th>HARGA</th><th>JUMLAH</th><th>VOL</th><th>HARGA</th><th>JUMLAH</th></tr>
    """
    tot_s_g, tot_m_g, tot_sel_g = 0, 0, 0
    for kro, g_kro in df_matrik.groupby('KRO'):
        k_kro, n_kro = split_kode(kro)
        tot_s_g += g_kro['Tot_s'].sum(); tot_m_g += g_kro['Tot_m'].sum(); tot_sel_g += g_kro['Selisih'].sum()
        html += f"<tr class='kro-row bold'><td>{k_kro}</td><td>{n_kro}</td><td></td><td></td><td class='right'>{format_rupiah(g_kro['Tot_s'].sum())}</td><td></td><td></td><td class='right'>{format_rupiah(g_kro['Tot_m'].sum())}</td><td class='right'>{format_rupiah(g_kro['Selisih'].sum())}</td></tr>"
        for ro, g_ro in g_kro.groupby('RO'):
            k_ro, n_ro = split_kode(ro)
            html += f"<tr class='ro-row bold'><td>{k_ro}</td><td>{n_ro}</td><td></td><td></td><td class='right'>{format_rupiah(g_ro['Tot_s'].sum())}</td><td></td><td></td><td class='right'>{format_rupiah(g_ro['Tot_m'].sum())}</td><td class='right'>{format_rupiah(g_ro['Selisih'].sum())}</td></tr>"
            for komp, g_komp in g_ro.groupby('Komponen'):
                k_komp, n_komp = split_kode(komp)
                html += f"<tr class='komp-row bold'><td>{k_komp}</td><td>{n_komp}</td><td></td><td></td><td class='right'>{format_rupiah(g_komp['Tot_s'].sum())}</td><td></td><td></td><td class='right'>{format_rupiah(g_komp['Tot_m'].sum())}</td><td class='right'>{format_rupiah(g_komp['Selisih'].sum())}</td></tr>"
                for sub, g_sub in g_komp.groupby('Sub_Komponen'):
                    if sub and sub != "-":
                        k_sub, n_sub = split_kode(sub)
                        html += f"<tr class='sub-row bold'><td>{k_sub}</td><td>{n_sub}</td><td></td><td></td><td class='right'>{format_rupiah(g_sub['Tot_s'].sum())}</td><td></td><td></td><td class='right'>{format_rupiah(g_sub['Tot_m'].sum())}</td><td class='right'>{format_rupiah(g_sub['Selisih'].sum())}</td></tr>"
                    for keg, g_keg in g_sub.groupby('Kegiatan'):
                        html += f"<tr class='keg-row bold'><td>{keg_map.get(keg, '0000')}</td><td style='padding-left:10px;'>{keg.title()}</td><td></td><td></td><td class='right'>{format_rupiah(g_keg['Tot_s'].sum())}</td><td></td><td></td><td class='right'>{format_rupiah(g_keg['Tot_m'].sum())}</td><td class='right'>{format_rupiah(g_keg['Selisih'].sum())}</td></tr>"
                        for akun, g_akun in g_keg.groupby('Akun_Belanja'):
                            k_ak, n_ak = split_kode(akun)
                            html += f"<tr class='bold'><td>{k_ak}</td><td style='padding-left:20px;'>{n_ak}</td><td></td><td></td><td class='right'>{format_rupiah(g_akun['Tot_s'].sum())}</td><td></td><td></td><td class='right'>{format_rupiah(g_akun['Tot_m'].sum())}</td><td class='right'>{format_rupiah(g_akun['Selisih'].sum())}</td></tr>"
                            for _, det in g_akun.iterrows():
                                v_s = get_vol_sat_combined(det['V1_s'], det['S1_s'], det['V2_s'], det['S2_s']) if det['Tot_s'] > 0 else "-"
                                v_m = get_vol_sat_combined(det['V1_m'], det['S1_m'], det['V2_m'], det['S2_m']) if det['Tot_m'] > 0 else "-"
                                html += f"<tr><td></td><td style='padding-left:30px;'>- {det['Uraian']}</td><td class='center'>{v_s}</td><td class='right'>{format_rupiah(det['Hrg_s']) if det['Tot_s']>0 else '-'}</td><td class='right'>{format_rupiah(det['Tot_s'])}</td><td class='center'>{v_m}</td><td class='right'>{format_rupiah(det['Hrg_m']) if det['Tot_m']>0 else '-'}</td><td class='right'>{format_rupiah(det['Tot_m'])}</td><td class='right'>{format_rupiah(det['Selisih'])}</td></tr>"
    html += f"""<tr class='bold' style='background-color:#d9d9d9;'><td colspan='2' class='right'>TOTAL GLOBAL</td><td></td><td></td><td class='right'>Rp {format_rupiah(tot_s_g)}</td><td></td><td></td><td class='right'>Rp {format_rupiah(tot_m_g)}</td><td class='right'>Rp {format_rupiah(tot_sel_g)}</td></tr></table>
    <div class="ttd-box">Samarinda, {tgl_cetak}<br>Dekan<br><br><br><br><br><b><u>{nama_dekan}</u></b><br>NIP. {nip_dekan}</div>{paraf_html}</body></html>"""
    return html

col_m1, col_m2, col_m3 = st.columns(3)
tgl_skrg_matrik = format_tgl_indo(datetime.now().strftime("%Y-%m-%d"))
tgl_cetak_matrik = col_m1.text_input("Tanggal Cetak Matrik", value=tgl_skrg_matrik, key="tgl_matrik")
dekan_matrik = col_m2.text_input("Nama Dekan", value="Prof. Dr. M. Bahri Arifin, M.Hum.", key="dek_matrik")
nip_matrik = col_m3.text_input("NIP Dekan", value="196211271989031004", key="nip_matrik")

if df_rab_utama.empty:
    st.warning("Belum ada data untuk dibandingkan.")
else:
    list_all_versions = sorted(df_rab_utama['Versi_RAB'].unique())
    col_v1, col_v2 = st.columns(2)
    v1_def = list_all_versions[0] if len(list_all_versions) > 0 else None
    v2_def = list_all_versions[1] if len(list_all_versions) > 1 else v1_def
    pilih_v1 = col_v1.selectbox("Pilih Versi Semula (Sebelum):", list_all_versions, index=list_all_versions.index(v1_def) if v1_def else 0)
    pilih_v2 = col_v2.selectbox("Pilih Versi Menjadi (Sesudah):", list_all_versions, index=list_all_versions.index(v2_def) if v2_def else 0)
    
    sumber_dana_matrik = st.radio("Pilih Sumber Dana Matrik:", ["BOPTN", "PNBP"], key="sd_matrik", horizontal=True)
    tampilkan_paraf_matrik = st.checkbox("Tampilkan Tabel Paraf (Khusus Arsip Hardcopy Internal)", key="paraf_matrik")
    
    if st.button("🔍 Generate Matrik Perbandingan", type="primary"):
        df_u1 = df_rab_utama[(df_rab_utama['Versi_RAB'] == pilih_v1) & (df_rab_utama['Sumber_Dana'] == sumber_dana_matrik)]
        df_d1 = df_rab_detail[df_rab_detail['ID_RAB'].isin(df_u1['ID_RAB'])]
        df_m1 = pd.merge(df_d1, df_u1, on='ID_RAB') if not df_u1.empty else pd.DataFrame()
        
        df_u2 = df_rab_utama[(df_rab_utama['Versi_RAB'] == pilih_v2) & (df_rab_utama['Sumber_Dana'] == sumber_dana_matrik)]
        df_d2 = df_rab_detail[df_rab_detail['ID_RAB'].isin(df_u2['ID_RAB'])]
        df_m2 = pd.merge(df_d2, df_u2, on='ID_RAB') if not df_u2.empty else pd.DataFrame()
        
        keys = ['Sumber_Dana', 'KRO', 'RO', 'Komponen', 'Sub_Komponen', 'Kegiatan', 'Akun_Belanja', 'Uraian']
        agg_dict = {'Vol_1': 'first', 'Sat_1': 'first', 'Vol_2': 'first', 'Sat_2': 'first', 'Harga_Satuan': 'first', 'Total_Biaya': 'sum'}
        
        df_m1 = df_m1.groupby(keys).agg(agg_dict).reset_index() if not df_m1.empty else pd.DataFrame(columns=keys + list(agg_dict.keys()))
        df_m2 = df_m2.groupby(keys).agg(agg_dict).reset_index() if not df_m2.empty else pd.DataFrame(columns=keys + list(agg_dict.keys()))
        
        df_m1.rename(columns={'Vol_1':'V1_s', 'Sat_1':'S1_s', 'Vol_2':'V2_s', 'Sat_2':'S2_s', 'Harga_Satuan':'Hrg_s', 'Total_Biaya':'Tot_s'}, inplace=True)
        df_m2.rename(columns={'Vol_1':'V1_m', 'Sat_1':'S1_m', 'Vol_2':'V2_m', 'Sat_2':'S2_m', 'Harga_Satuan':'Hrg_m', 'Total_Biaya':'Tot_m'}, inplace=True)
        
        df_matrik = pd.merge(df_m1, df_m2, on=keys, how='outer')
        for c in ['V1_s', 'V2_s', 'Hrg_s', 'Tot_s', 'V1_m', 'V2_m', 'Hrg_m', 'Tot_m']: df_matrik[c] = df_matrik.get(c, pd.Series(0)).fillna(0)
        for c in ['S1_s', 'S2_s', 'S1_m', 'S2_m']: df_matrik[c] = df_matrik.get(c, pd.Series("")).fillna("")
        df_matrik['Selisih'] = df_matrik['Tot_m'] - df_matrik['Tot_s']
        
        if df_matrik.empty: st.info(f"Tidak ada data rincian pada kedua versi untuk {sumber_dana_matrik}.")
        else:
            html_matrik = generate_matrik_html(df_matrik, pilih_v1, pilih_v2, kegiatan_code_map, tahun_aktif, tgl_cetak_matrik, dekan_matrik, nip_matrik, sumber_dana_matrik, tampilkan_paraf_matrik)
            with st.container(border=True): components.html(html_matrik, height=600, scrolling=True)
            st.download_button("📥 Cetak Matrik Perubahan (.html)", data=html_matrik.encode('utf-8'), file_name=f"Matrik_{sumber_dana_matrik}_{tahun_aktif}_{pilih_v1}_vs_{pilih_v2}.html", mime="text/html")

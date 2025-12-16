# Nama fail: app.py
import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import io
import plotly.express as px
from supabase import create_client, Client
import openpyxl # Pastikan ini ada dalam requirements.txt

# --- TETAPAN HALAMAN (MESTI DI ATAS SEKALI) ---
st.set_page_config(layout="wide", page_title="Sistem Gaji Sawit")

# ==============================================================================
# 1. SAMBUNGAN KE SUPABASE (DIPINDAHKAN KE ATAS)
# ==============================================================================
# Kita menyambung ke database SEBELUM meminta password.
# Ini membolehkan "Bot" cron-job mengekalkan database aktif tanpa perlu login.
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
    
    # "Ping" database: Kita minta 1 data kosong sahaja untuk memastikan sambungan berjaya
    # Ini adalah 'signal' kepada Supabase bahawa aplikasi sedang aktif
    try:
        supabase.table('rekod_kos').select("id").limit(1).execute()
    except Exception:
        pass # Abaikan jika ada ralat kecil, asalkan signal dihantar

except KeyError:
    st.error("Ralat: Rahsia 'SUPABASE_URL' atau 'SUPABASE_KEY' tidak ditemui.")
    st.stop()
except Exception as e:
    # Jangan hentikan app sepenuhnya jika cuma ralat sambungan sementara, tapi log ia
    print(f"Status Sambungan: {e}")

# ==============================================================================
# 2. FUNGSI LOG MASUK & KESELAMATAN
# ==============================================================================
def check_password():
    """Returns True if user has entered the correct password."""
    if "logged_in" in st.session_state and st.session_state["logged_in"] == True:
        return True
    try:
        correct_password = st.secrets["APP_PASSWORD"]
    except KeyError:
        st.error("Ralat: Rahsia 'APP_PASSWORD' tidak ditemui.")
        return False

    st.warning("🔒 Sila masukkan kata laluan untuk mengakses aplikasi ini.")
    password = st.text_input("Kata Laluan:", type="password")

    if st.button("Log Masuk"):
        if password == correct_password:
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Kata laluan salah.")
    return False

# PENTING: Semakan password berlaku DI SINI.
# Bot akan terhenti di sini (data selamat), tetapi database sudah 'ping' di atas.
if not check_password():
    st.stop()

# ==============================================================================
# 3. FUNGSI-FUNGSI LOGIK (KIRAAN, PDF, EXCEL)
# ==============================================================================

def kira_payroll(senarai_resit, total_kos):
    KADAR_LORI_PER_KG = 0.07
    jumlah_hasil_jualan = sum(resit['Hasil_RM'] for resit in senarai_resit)
    jumlah_berat_kg = sum(resit['Berat_kg'] for resit in senarai_resit)
    gaji_lori = jumlah_berat_kg * KADAR_LORI_PER_KG
    baki_bersih = jumlah_hasil_jualan - gaji_lori - total_kos
    gaji_penumbak = baki_bersih / 2
    bahagian_pemilik = baki_bersih / 2
    data_kiraan = {
        "jumlah_hasil_jualan": jumlah_hasil_jualan,
        "jumlah_berat_kg": jumlah_berat_kg,
        "jumlah_berat_mt": jumlah_berat_kg / 1000,
        "gaji_lori": gaji_lori,
        "total_kos_operasi": total_kos,
        "baki_bersih": baki_bersih,
        "gaji_penumbak": gaji_penumbak,
        "bahagian_pemilik": bahagian_pemilik,
        "kadar_lori_per_kg": KADAR_LORI_PER_KG
    }
    return data_kiraan

def jana_pdf_binary(bulan_tahun, senarai_resit, data_kiraan):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.set_font("Helvetica", 'B', 18)
    pdf.cell(0, 10, f"LADANG SAWIT SATIN LUNG MANIS", ln=True, align='C')
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, f"Laporan Kiraan Gaji - {bulan_tahun}", ln=True, align='C')
    pdf.ln(10)
    
    # Bahagian 1: Jualan
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "Bahagian 1: Butiran Jualan (Resit)", ln=True)
    pdf.set_font("Helvetica", size=11)
    for i, resit in enumerate(senarai_resit):
        gred = resit.get('Gred', 'N/A')
        berat_kg = resit.get('Berat_kg', 0)
        harga_per_mt = resit.get('Harga_RM_per_MT', 0)
        hasil_resit = resit.get('Hasil_RM', 0)
        
        teks_resit = f"  Resit #{i+1} (Gred {gred}): {berat_kg:.2f} kg @ RM{harga_per_mt:.2f}/MT = RM{hasil_resit:.2f}"
        pdf.cell(0, 8, teks_resit, ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 8, f"Jumlah Berat Keseluruhan: {data_kiraan.get('jumlah_berat_kg', 0):.2f} kg", ln=True)
    pdf.cell(0, 8, f"Jumlah Hasil Jualan Kasar: RM{data_kiraan.get('jumlah_hasil_jualan', 0):.2f}", ln=True)
    pdf.ln(10)

    # Bahagian 2: Kiraan Gaji
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "Bahagian 2: Pengiraan Gaji dan Pembahagian", ln=True)
    
    # Gaji Lori
    pdf.set_font("Helvetica", 'BU', 11)
    pdf.cell(0, 8, "Gaji Pekerja 1 (Lori):", ln=True)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"  Kiraan: {data_kiraan.get('jumlah_berat_kg', 0):.2f} kg x RM{data_kiraan.get('kadar_lori_per_kg', 0.07):.2f}/kg", ln=True)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 8, f"  Jumlah Gaji Lori = RM{data_kiraan.get('gaji_lori', 0):.2f}", ln=True)
    pdf.ln(5)

    # Kos Operasi
    pdf.set_font("Helvetica", 'BU', 11)
    pdf.cell(0, 8, "Kos Operasi Bulanan (Baja, Racun, dll):", ln=True)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 8, f"  Jumlah Kos Operasi = RM{data_kiraan.get('total_kos_operasi', 0):.2f}", ln=True)
    pdf.ln(5)

    # Baki Bersih
    pdf.set_font("Helvetica", 'BU', 11)
    pdf.cell(0, 8, "Hasil Bersih (Untuk Dibahagi):", ln=True)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"  Kiraan: RM{data_kiraan.get('jumlah_hasil_jualan', 0):.2f} (Jualan) - RM{data_kiraan.get('gaji_lori', 0):.2f} (Lori) - RM{data_kiraan.get('total_kos_operasi', 0):.2f} (Kos Operasi)", ln=True)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 8, f"  Hasil Bersih = RM{data_kiraan.get('baki_bersih', 0):.2f}", ln=True)
    pdf.ln(5)

    # Pembahagian 50/50
    pdf.set_font("Helvetica", 'BU', 11)
    pdf.cell(0, 8, "Pembahagian Hasil Bersih (50/50):", ln=True)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"  Kiraan: RM{data_kiraan.get('baki_bersih', 0):.2f} / 2", ln=True)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 8, f"  Gaji Pekerja 2 (Penumbak) = RM{data_kiraan.get('gaji_penumbak', 0):.2f}", ln=True)
    pdf.cell(0, 8, f"  Bahagian Pemilik Ladang = RM{data_kiraan.get('bahagian_pemilik', 0):.2f}", ln=True)
    pdf.ln(15)
    
    # Footer
    pdf.set_font("Helvetica", 'I', 9)
    pdf.cell(0, 5, "Laporan ini disediakan oleh:", ln=True, align='L')
    pdf.set_font("Helvetica", 'B', 9)
    pdf.cell(0, 5, "Mohamad Saifullah Satin", ln=True, align='L')
    pdf.set_font("Helvetica", 'I', 9)
    pdf.cell(0, 5, "Telefon: 019-840 6421", ln=True, align='L')
    pdf.cell(0, 5, "Email: msaifullahsatin@gmail.com", ln=True, align='L')
    tarikh_jana = datetime.date.today().strftime("%d-%m-%Y")
    pdf.set_y(-15)
    pdf.set_font("Helvetica", 'I', 8)
    pdf.cell(0, 10, f"Laporan dijana secara automatik pada {tarikh_jana}", ln=True, align='C')
    return bytes(pdf.output(dest='S'))

def jana_pdf_berkelompok(laporan_title, df_gaji_filtered, df_jualan_filtered, df_kos_filtered):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    
    # 1. Tajuk
    pdf.set_font("Helvetica", 'B', 18)
    pdf.cell(0, 10, f"LADANG SAWIT SATIN LUNG MANIS", ln=True, align='C')
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, f"Ringkasan Laporan - {laporan_title}", ln=True, align='C')
    pdf.ln(10)

    # 2. Ringkasan Keseluruhan (KPI)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "Ringkasan Prestasi Keseluruhan", ln=True)
    
    total_jualan = df_gaji_filtered['JumlahJualan_RM'].sum()
    total_berat = df_gaji_filtered['JumlahBerat_kg'].sum()
    total_gaji_lori = df_gaji_filtered['GajiLori_RM'].sum()
    total_kos_ops = df_gaji_filtered.get('total_kos_operasi', 0.0).sum()
    total_gaji_penumbak = df_gaji_filtered['GajiPenumbak_RM'].sum()
    total_bahagian_pemilik = df_gaji_filtered['BahagianPemilik_RM'].sum()
    
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 8, f"Jumlah Jualan Kasar: RM {total_jualan:,.2f}", ln=True)
    pdf.cell(0, 8, f"Jumlah Berat Jualan: {total_berat:,.2f} kg", ln=True)
    pdf.cell(0, 8, f"Jumlah Kos Operasi: RM {total_kos_ops:,.2f}", ln=True)
    pdf.cell(0, 8, f"Jumlah Gaji Lori: RM {total_gaji_lori:,.2f}", ln=True)
    pdf.cell(0, 8, f"Jumlah Gaji Penumbak: RM {total_gaji_penumbak:,.2f}", ln=True)
    pdf.cell(0, 8, f"Jumlah Bahagian Pemilik: RM {total_bahagian_pemilik:,.2f}", ln=True)
    pdf.ln(10)

    # 3. Jadual Ringkasan Mengikut Bulan
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "Pecahan Mengikut Bulan", ln=True)
    
    w_bulan = 40
    w_angka = 25 
    
    pdf.set_font("Helvetica", 'B', 8)
    pdf.cell(w_bulan, 8, "Bulan", 1, align='C')
    pdf.cell(w_angka, 8, "Jualan (RM)", 1, align='C')
    pdf.cell(w_angka, 8, "Kos Ops (RM)", 1, align='C')
    pdf.cell(w_angka, 8, "Gaji Lori (RM)", 1, align='C')
    pdf.cell(w_angka, 8, "Gaji Pnumbak (RM)", 1, align='C')
    pdf.cell(w_angka, 8, "Pemilik (RM)", 1, align='C')
    pdf.cell(w_angka, 8, "Berat (kg)", 1, ln=True, align='C')

    pdf.set_font("Helvetica", '', 8)
    try:
        peta_bulan = {
            "Januari": 1, "Februari": 2, "Mac": 3, "April": 4, "Mei": 5, "Jun": 6,
            "Julai": 7, "Ogos": 8, "September": 9, "Oktober": 10, "November": 11, "Disember": 12
        }
        df_gaji_filtered['BulanString'] = df_gaji_filtered['BulanTahun'].str.split(' ', expand=True)[0]
        df_gaji_filtered['Tahun'] = df_gaji_filtered['BulanTahun'].str.split(' ', expand=True)[1].astype(int)
        df_gaji_filtered['BulanNombor'] = df_gaji_filtered['BulanString'].map(peta_bulan)
        df_gaji_sorted = df_gaji_filtered.sort_values(by=['Tahun', 'BulanNombor'])
    except Exception:
        df_gaji_sorted = df_gaji_filtered
        
    for index, data in df_gaji_sorted.iterrows():
        pdf.cell(w_bulan, 8, data['BulanTahun'], 1)
        pdf.cell(w_angka, 8, f"{data['JumlahJualan_RM']:,.2f}", 1, align='R')
        pdf.cell(w_angka, 8, f"{data.get('total_kos_operasi', 0.0):,.2f}", 1, align='R')
        pdf.cell(w_angka, 8, f"{data['GajiLori_RM']:,.2f}", 1, align='R')
        pdf.cell(w_angka, 8, f"{data['GajiPenumbak_RM']:,.2f}", 1, align='R')
        pdf.cell(w_angka, 8, f"{data['BahagianPemilik_RM']:,.2f}", 1, align='R')
        pdf.cell(w_angka, 8, f"{data['JumlahBerat_kg']:,.2f}", 1, ln=True, align='R')
    
    pdf.ln(10)
    
    # 4. Ringkasan Pecahan Jualan (Gred) & Kos
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "Pecahan Keseluruhan (Gred & Kos)", ln=True)
    pdf.set_font("Helvetica", '', 11)

    # Pecahan Gred
    gred_a_berat = df_jualan_filtered[df_jualan_filtered['Gred'] == 'A']['Berat_kg'].sum()
    gred_a_hasil = df_jualan_filtered[df_jualan_filtered['Gred'] == 'A']['Hasil_RM'].sum()
    gred_b_berat = df_jualan_filtered[df_jualan_filtered['Gred'] == 'B']['Berat_kg'].sum()
    gred_b_hasil = df_jualan_filtered[df_jualan_filtered['Gred'] == 'B']['Hasil_RM'].sum()
    gred_c_berat = df_jualan_filtered[df_jualan_filtered['Gred'] == 'C']['Berat_kg'].sum()
    gred_c_hasil = df_jualan_filtered[df_jualan_filtered['Gred'] == 'C']['Hasil_RM'].sum()
    
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(95, 8, "Pecahan Jualan (Gred)", 1, ln=True, align='C')
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 8, f"Gred A: {gred_a_berat:,.2f} kg  |  RM {gred_a_hasil:,.2f}", ln=True)
    pdf.cell(0, 8, f"Gred B: {gred_b_berat:,.2f} kg  |  RM {gred_b_hasil:,.2f}", ln=True)
    pdf.cell(0, 8, f"Gred C: {gred_c_berat:,.2f} kg  |  RM {gred_c_hasil:,.2f}", ln=True)
    pdf.ln(5)

    # Pecahan Kos
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(95, 8, "Pecahan Kos Operasi", 1, ln=True, align='C')
    pdf.set_font("Helvetica", '', 10)
    if not df_kos_filtered.empty:
        kos_by_type = df_kos_filtered.groupby('JenisKos')['Jumlah_RM'].sum()
        for jenis, jumlah in kos_by_type.items():
            pdf.cell(0, 8, f"{jenis}: RM {jumlah:,.2f}", ln=True)
    else:
        pdf.cell(0, 8, "Tiada kos operasi direkodkan.", ln=True)
    
    # 5. Footer
    tarikh_jana = datetime.date.today().strftime("%d-%m-%Y")
    pdf.set_y(-15)
    pdf.set_font("Helvetica", 'I', 8)
    nama_anda = st.secrets.get('NAMA_ANDA', 'Admin')
    pdf.cell(0, 10, f"Laporan dijana secara automatik pada {tarikh_jana} oleh {nama_anda}", ln=True, align='C')
    
    return bytes(pdf.output(dest='S'))

def to_excel(df_gaji, df_jualan, df_kos):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_gaji.to_excel(writer, sheet_name='Ringkasan_Gaji', index=False)
        df_jualan.to_excel(writer, sheet_name='Butiran_Jualan', index=False)
        df_kos.to_excel(writer, sheet_name='Butiran_Kos', index=False)
    processed_data = output.getvalue()
    return processed_data

def proses_dataframe_bulanan(df_gaji_raw):
    """Memproses df_gaji untuk menambah kolum Tahun, BulanNombor, dan Keuntungan_RM."""
    if df_gaji_raw.empty:
        return pd.DataFrame(columns=['BulanTahun', 'Tahun', 'BulanNombor', 'BulanString', 'JumlahJualan_RM', 'total_kos_operasi', 'Keuntungan_RM'])

    df = df_gaji_raw.copy()
    
    # 1. Sediakan kolum kos
    if 'total_kos_operasi' not in df.columns:
        df['total_kos_operasi'] = 0.0
    df['total_kos_operasi'] = df['total_kos_operasi'].fillna(0)

    # 2. Kira Keuntungan (Jualan - Gaji Lori - Kos Ops)
    df['Keuntungan_RM'] = df['JumlahJualan_RM'] - df['GajiLori_RM'] - df['total_kos_operasi']

    # 3. Proses Bulan & Tahun untuk pengisihan
    try:
        peta_bulan = {
            "Januari": 1, "Februari": 2, "Mac": 3, "April": 4, "Mei": 5, "Jun": 6,
            "Julai": 7, "Ogos": 8, "September": 9, "Oktober": 10, "November": 11, "Disember": 12
        }
        df_split = df['BulanTahun'].str.split(' ', expand=True)
        df['BulanString'] = df_split[0]
        df['Tahun'] = df_split[1].astype(int)
        df['BulanNombor'] = df['BulanString'].map(peta_bulan)
    except Exception as e:
        # Jika ralat format, guna dummy
        df['Tahun'] = 2000
        df['BulanNombor'] = 1
        df['BulanString'] = 'N/A'

    return df

# ==============================================================================
# 4. MUATKAN DATA & PROSES AWAL
# ==============================================================================
@st.cache_data(ttl=600)
def muat_data():
    try:
        response_gaji = supabase.table('rekod_gaji').select("*").order('id', desc=False).execute()
        df_gaji = pd.DataFrame(response_gaji.data)
        
        response_jualan = supabase.table('rekod_jualan').select("*").order('id', desc=False).execute()
        df_jualan = pd.DataFrame(response_jualan.data)
        
        response_kos = supabase.table('rekod_kos').select("*").order('id', desc=False).execute()
        df_kos = pd.DataFrame(response_kos.data)
        
        # Kolum Jangkaan
        expected_gaji_cols = ['BulanTahun', 'JumlahJualan_RM', 'JumlahBerat_kg', 'GajiLori_RM', 
                              'GajiPenumbak_RM', 'BahagianPemilik_RM', 'total_kos_operasi', 
                              'id', 'created_at']
        expected_jualan_cols = ['BulanTahun', 'IDResit', 'Gred', 'Berat_kg', 
                                'Harga_RM_per_MT', 'Hasil_RM', 'id', 'created_at']
        expected_kos_cols = ['BulanTahun', 'JenisKos', 'Jumlah_RM', 'id', 'created_at']

        # Cipta DataFrame kosong dengan kolum jika data tiada
        if df_gaji.empty:
            df_gaji = pd.DataFrame(columns=expected_gaji_cols)
        if df_jualan.empty:
            df_jualan = pd.DataFrame(columns=expected_jualan_cols)
        if df_kos.empty:
            df_kos = pd.DataFrame(columns=expected_kos_cols)

        return df_gaji, df_jualan, df_kos
    
    except Exception as e:
        st.error(f"Ralat membaca data dari Supabase: {e}")
        return (pd.DataFrame(), pd.DataFrame(), pd.DataFrame())

df_gaji_raw, df_jualan_raw, df_kos_raw = muat_data()

# Proses data untuk graf (diperlukan di dashboard)
df_gaji_processed = proses_dataframe_bulanan(df_gaji_raw)

# ==============================================================================
# 5. PAPARAN UTAMA & NAVIGASI
# ==============================================================================
st.title("Sistem Pengurusan Ladang Sawit 🧑‍🌾")

st.sidebar.title("Navigasi")
page = st.sidebar.radio("Pilih Halaman:", ["📊 Dashboard Statistik", 
                                          "📝 Kemasukan Data Baru", 
                                          "🖨️ Urus & Cetak Semula", 
                                          "📈 Laporan Berkelompok"])

if st.sidebar.button("Segarkan Semula Data (Refresh)"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.error("Klik untuk keluar dari sistem.")
if st.sidebar.button("Log Keluar"):
    st.session_state["logged_in"] = False
    st.rerun()

# ==============================================================================
# HALAMAN 1: DASHBOARD
# ==============================================================================
if page == "📊 Dashboard Statistik":
    st.header("📊 Dashboard Statistik")
    
    tab_tren, tab_perbandingan = st.tabs(["📈 Tren Keseluruhan", "⚖️ Perbandingan Tahun-ke-Tahun"])

    with tab_tren:
        if df_gaji_processed.empty:
            st.warning("Tiada data untuk dipaparkan. Sila ke halaman 'Kemasukan Data Baru' untuk menambah data.")
        else:
            # KPI
            total_sales = df_gaji_processed['JumlahJualan_RM'].sum()
            total_weight_kg = df_gaji_processed['JumlahBerat_kg'].sum()
            avg_monthly_owner = df_gaji_processed['BahagianPemilik_RM'].mean()

            col1, col2, col3 = st.columns(3)
            col1.metric("Jumlah Jualan Keseluruhan", f"RM{total_sales:,.2f}")
            col2.metric("Jumlah Berat Keseluruhan", f"{total_weight_kg:,.0f} kg")
            col3.metric("Purata Pendapatan Bulanan (Pemilik)", f"RM{avg_monthly_owner:,.2f}")
            st.markdown("---")
            
            # Graf Tren
            st.subheader("Tren Jualan, Kos, dan Keuntungan")
            df_gaji_sorted = df_gaji_processed.sort_values(by=['Tahun', 'BulanNombor'])
                
            fig_tren_gaji = px.line(
                df_gaji_sorted, 
                x='BulanTahun', 
                y=['JumlahJualan_RM', 'total_kos_operasi', 'Keuntungan_RM', 'BahagianPemilik_RM'],
                title="Perbandingan Jualan, Kos, dan Keuntungan",
                labels={'value': 'Jumlah (RM)', 'BulanTahun': 'Bulan'},
                markers=True
            )
            st.plotly_chart(fig_tren_gaji, use_container_width=True)
            
            # Analisis Pecahan
            st.subheader("Analisis Pecahan")
            col_gred1, col_gred2 = st.columns(2)
            
            df_jualan_paparan = df_jualan_raw.drop(columns=['id', 'created_at'], errors='ignore') if not df_jualan_raw.empty else df_jualan_raw
            df_kos_paparan = df_kos_raw.drop(columns=['id', 'created_at'], errors='ignore') if not df_kos_raw.empty else df_kos_raw

            with col_gred1:
                fig_pie_hasil = px.pie(
                    df_jualan_paparan, names='Gred', values='Hasil_RM', 
                    title="Pecahan Hasil Jualan (RM) mengikut Gred"
                )
                st.plotly_chart(fig_pie_hasil, use_container_width=True)
            
            with col_gred2:
                if not df_kos_paparan.empty and df_kos_paparan['Jumlah_RM'].sum() > 0:
                    fig_pie_kos = px.pie(
                        df_kos_paparan, names='JenisKos', values='Jumlah_RM',
                        title="Pecahan Kos Operasi mengikut Jenis"
                    )
                    st.plotly_chart(fig_pie_kos, use_container_width=True)
                else:
                    st.info("Tiada data kos operasi direkodkan.")
            
            st.markdown("---")
            st.subheader("Data Mentah (dari Database)")
            st.write("Data Gaji (Ringkasan Bulanan)")
            st.dataframe(df_gaji_raw.drop(columns=['id', 'created_at'], errors='ignore'))
            st.write("Data Jualan (Butiran Resit)")
            st.dataframe(df_jualan_raw.drop(columns=['id', 'created_at'], errors='ignore'))
            st.write("Data Kos Operasi")
            st.dataframe(df_kos_raw.drop(columns=['id', 'created_at'], errors='ignore'))

    with tab_perbandingan:
        st.subheader("Perbandingan Prestasi Tahun-ke-Tahun")
        
        available_years = sorted(df_gaji_processed['Tahun'].unique(), reverse=True)
        
        if len(available_years) < 2:
            st.info("Perlukan sekurang-kurangnya 2 tahun data untuk membuat perbandingan.")
        else:
            col_y1, col_y2 = st.columns(2)
            year_1 = col_y1.selectbox("Pilih Tahun Pertama:", available_years, index=1)
            year_2 = col_y2.selectbox("Pilih Tahun Kedua:", available_years, index=0)

            if year_1 == year_2:
                st.error("Sila pilih dua tahun yang berbeza.")
            else:
                peta_bulan_inv = {
                    1: "Jan", 2: "Feb", 3: "Mac", 4: "Apr", 5: "Mei", 6: "Jun",
                    7: "Jul", 8: "Ogos", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Dis"
                }
                
                df_y1 = df_gaji_processed[df_gaji_processed['Tahun'] == year_1][['BulanNombor', 'JumlahJualan_RM', 'total_kos_operasi', 'Keuntungan_RM']]
                df_y1 = df_y1.add_suffix(f"_{year_1}")
                df_y1.rename(columns={f'BulanNombor_{year_1}': 'BulanNombor'}, inplace=True)

                df_y2 = df_gaji_processed[df_gaji_processed['Tahun'] == year_2][['BulanNombor', 'JumlahJualan_RM', 'total_kos_operasi', 'Keuntungan_RM']]
                df_y2 = df_y2.add_suffix(f"_{year_2}")
                df_y2.rename(columns={f'BulanNombor_{year_2}': 'BulanNombor'}, inplace=True)
                
                df_merged = pd.merge(df_y1, df_y2, on='BulanNombor', how='outer').fillna(0)
                df_merged['Bulan'] = df_merged['BulanNombor'].map(peta_bulan_inv)
                df_merged = df_merged.sort_values(by='BulanNombor')

                fig_jualan = px.bar(
                    df_merged, 
                    x='Bulan', 
                    y=[f'JumlahJualan_RM_{year_1}', f'JumlahJualan_RM_{year_2}'],
                    barmode='group',
                    title=f"Perbandingan Jualan Kasar ({year_1} vs {year_2})",
                    labels={'value': 'Jumlah (RM)', 'variable': 'Tahun'}
                )
                st.plotly_chart(fig_jualan, use_container_width=True)

                fig_keuntungan = px.bar(
                    df_merged, 
                    x='Bulan', 
                    y=[f'Keuntungan_RM_{year_1}', f'Keuntungan_RM_{year_2}'],
                    barmode='group',
                    title=f"Perbandingan Keuntungan Bersih ({year_1} vs {year_2})",
                    labels={'value': 'Jumlah (RM)', 'variable': 'Tahun'}
                )
                st.plotly_chart(fig_keuntungan, use_container_width=True)

# ==============================================================================
# HALAMAN 2: KEMASUKAN DATA
# ==============================================================================
elif page == "📝 Kemasukan Data Baru":
    st.header("📝 Kemasukan Data Jualan Bulanan Baru")
    
    tab_jualan, tab_kos = st.tabs(["1. Masukkan Jualan (Gaji)", "2. Masukkan Kos Operasi"])
    senarai_bulan = ["Januari", "Februari", "Mac", "April", "Mei", "Jun", 
                    "Julai", "Ogos", "September", "Oktober", "November", "Disember"]
    tahun_semasa = datetime.date.today().year
    senarai_tahun = list(range(tahun_semasa - 5, tahun_semasa + 2)) 
    senarai_tahun.reverse()

    with tab_jualan:
        st.subheader("Borang Kiraan Gaji")
        with st.form("borang_data_gaji"):
            col1, col2 = st.columns(2)
            with col1:
                bulan_gaji = st.selectbox("Pilih Bulan:", senarai_bulan, index=datetime.date.today().month - 1, key="bulan_gaji") 
            with col2:
                tahun_gaji = st.selectbox("Pilih Tahun:", senarai_tahun, key="tahun_gaji")
            bulan_tahun_gaji = f"{bulan_gaji} {tahun_gaji}"
            st.info(f"Anda sedang mengira gaji untuk: **{bulan_tahun_gaji}**")
            
            st.subheader("B. Butiran Resit Jualan")
            df_resit_input = pd.DataFrame([
                {"Gred": "A", "Berat_kg": 0.0, "Harga_RM_per_MT": 0.0},
                {"Gred": "B", "Berat_kg": 0.0, "Harga_RM_per_MT": 0.0},
                {"Gred": "C", "Berat_kg": 0.0, "Harga_RM_per_MT": 0.0},
            ])
            edited_df_jualan = st.data_editor(
                df_resit_input, num_rows="dynamic",
                column_config={
                    "Gred": st.column_config.SelectboxColumn("Gred", options=["A", "B", "C"], required=True),
                    "Berat_kg": st.column_config.NumberColumn("Berat (kg)", min_value=0.0, format="%.2f", required=True),
                    "Harga_RM_per_MT": st.column_config.NumberColumn("Harga Jualan (RM/MT)", min_value=0.0, format="%.2f", required=True)
                },
                key="data_editor_jualan"
            )
            submit_button_gaji = st.form_submit_button(label="Kira, Jana PDF & Simpan Gaji")

    with tab_kos:
        st.subheader("Borang Kemasukan Kos Operasi")
        with st.form("borang_data_kos"):
            col1_kos, col2_kos = st.columns(2)
            with col1_kos:
                bulan_kos = st.selectbox("Pilih Bulan:", senarai_bulan, index=datetime.date.today().month - 1, key="bulan_kos") 
            with col2_kos:
                tahun_kos = st.selectbox("Pilih Tahun:", senarai_tahun, key="tahun_kos")
            bulan_tahun_kos = f"{bulan_kos} {tahun_kos}"
            st.info(f"Anda sedang memasukkan kos untuk: **{bulan_tahun_kos}**")
            
            df_kos_input = pd.DataFrame([
                {"JenisKos": "Baja", "Jumlah_RM": 0.0},
                {"JenisKos": "Racun", "Jumlah_RM": 0.0},
            ])
            edited_df_kos = st.data_editor(
                df_kos_input, num_rows="dynamic",
                column_config={
                    "JenisKos": st.column_config.TextColumn("Jenis Kos", required=True),
                    "Jumlah_RM": st.column_config.NumberColumn("Jumlah (RM)", min_value=0.0, format="%.2f", required=True)
                },
                key="data_editor_kos"
            )
            submit_button_kos = st.form_submit_button(label="Simpan Kos ke Database")

    if submit_button_kos:
        if edited_df_kos['Jumlah_RM'].sum() == 0:
            st.error("Sila masukkan sekurang-kurangnya satu kos > 0.")
        else:
            with st.spinner("Menyimpan kos..."):
                senarai_kos = edited_df_kos[edited_df_kos['Jumlah_RM'] > 0].to_dict('records')
                for kos in senarai_kos:
                    kos['BulanTahun'] = bulan_tahun_kos
                
                try:
                    if not df_kos_raw.empty and bulan_tahun_kos in df_kos_raw['BulanTahun'].values:
                        supabase.table('rekod_kos').delete().eq('BulanTahun', bulan_tahun_kos).execute()
                    
                    supabase.table('rekod_kos').insert(senarai_kos).execute()
                    st.cache_data.clear()
                    st.success(f"Data kos untuk {bulan_tahun_kos} disimpan!")
                except Exception as e:
                    st.error(f"RALAT: {e}")

    if submit_button_gaji:
        if not bulan_tahun_gaji:
            st.error("Sila pilih Bulan dan Tahun.")
        elif edited_df_jualan['Berat_kg'].sum() == 0:
            st.error("Sila masukkan sekurang-kurangnya satu resit.")
        elif not df_gaji_raw.empty and bulan_tahun_gaji in df_gaji_raw['BulanTahun'].values:
            st.error(f"Data gaji untuk {bulan_tahun_gaji} sudah wujud.")
        else:
            with st.spinner("Mengira..."):
                kos_bulan_ini = df_kos_raw[df_kos_raw['BulanTahun'] == bulan_tahun_gaji]['Jumlah_RM'].sum() if not df_kos_raw.empty else 0.0
                
                senarai_resit = edited_df_jualan[edited_df_jualan['Berat_kg'] > 0].to_dict('records')
                for i, resit in enumerate(senarai_resit):
                    resit['Hasil_RM'] = (resit['Berat_kg'] / 1000) * resit['Harga_RM_per_MT']
                    resit['BulanTahun'] = bulan_tahun_gaji
                    resit['IDResit'] = i + 1

                data_kiraan = kira_payroll(senarai_resit, kos_bulan_ini)
                pdf_binary = jana_pdf_binary(bulan_tahun_gaji, senarai_resit, data_kiraan)
                
                data_gaji_dict = {
                    'BulanTahun': bulan_tahun_gaji,
                    'JumlahJualan_RM': data_kiraan['jumlah_hasil_jualan'],
                    'JumlahBerat_kg': data_kiraan['jumlah_berat_kg'],
                    'GajiLori_RM': data_kiraan['gaji_lori'],
                    'GajiPenumbak_RM': data_kiraan['gaji_penumbak'],
                    'BahagianPemilik_RM': data_kiraan['bahagian_pemilik'],
                    'total_kos_operasi': data_kiraan['total_kos_operasi']
                }
                
                data_jualan_list = [
                    {
                        'BulanTahun': r['BulanTahun'], 'IDResit': r['IDResit'], 'Gred': r['Gred'],
                        'Berat_kg': r['Berat_kg'], 'Harga_RM_per_MT': r['Harga_RM_per_MT'], 'Hasil_RM': r['Hasil_RM']
                    } for r in senarai_resit
                ]
                
                try:
                    supabase.table('rekod_gaji').insert(data_gaji_dict).execute()
                    supabase.table('rekod_jualan').insert(data_jualan_list).execute()
                    st.cache_data.clear()
                    st.success("Berjaya disimpan!")
                except Exception as e:
                    st.error(f"RALAT: {e}")
                    st.stop()

                nama_fail_pdf = f"Laporan_Gaji_{bulan_tahun_gaji.replace(' ', '_')}.pdf"
                st.download_button("Muat Turun PDF", data=pdf_binary, file_name=nama_fail_pdf, mime="application/pdf")

# ==============================================================================
# HALAMAN 3: URUS & CETAK SEMULA
# ==============================================================================
elif page == "🖨️ Urus & Cetak Semula":
    st.header("🖨️ Urus & Cetak Semula Laporan")
    
    if df_gaji_raw.empty:
        st.info("Tiada data.")
    else:
        senarai_bulan_rekod = df_gaji_raw['BulanTahun'].unique()
        
        # BAHAGIAN 1
        st.subheader("1. Cetak Semula Laporan PDF Bulanan")
        with st.form("borang_cetak_semula"):
            bulan_cetak = st.selectbox("Pilih Bulan:", senarai_bulan_rekod)
            if st.form_submit_button("Jana PDF"):
                data_gaji = df_gaji_raw[df_gaji_raw['BulanTahun'] == bulan_cetak].to_dict('records')[0]
                resit = df_jualan_raw[df_jualan_raw['BulanTahun'] == bulan_cetak].to_dict('records')
                
                kiraan = {
                    'jumlah_hasil_jualan': data_gaji['JumlahJualan_RM'],
                    'jumlah_berat_kg': data_gaji['JumlahBerat_kg'],
                    'gaji_lori': data_gaji['GajiLori_RM'],
                    'total_kos_operasi': data_gaji.get('total_kos_operasi', 0.0),
                    'kadar_lori_per_kg': 0.07, 
                    'baki_bersih': data_gaji['GajiPenumbak_RM'] + data_gaji['BahagianPemilik_RM'],
                    'gaji_penumbak': data_gaji['GajiPenumbak_RM'],
                    'bahagian_pemilik': data_gaji['BahagianPemilik_RM']
                }
                pdf = jana_pdf_binary(bulan_cetak, resit, kiraan)
                st.download_button(f"Muat Turun PDF {bulan_cetak}", pdf, f"Laporan_{bulan_cetak}.pdf", "application/pdf")
        
        st.divider()
        
        # BAHAGIAN 2 (EDIT)
        st.subheader("✏️ 2. Kemaskini Data Bulanan (Edit)")
        st.info("Pilih bulan, muatkan data, edit dan simpan.")
        
        if 'bulan_edit' not in st.session_state: st.session_state.bulan_edit = None
        
        c1, c2 = st.columns([3, 1])
        with c1: b_edit = st.selectbox("Pilih Bulan:", senarai_bulan_rekod, key="sel_edit")
        with c2: 
            st.write(" ")
            if st.button("Muatkan Data"): 
                st.session_state.bulan_edit = b_edit
                st.rerun()

        if st.session_state.bulan_edit:
            b_aktif = st.session_state.bulan_edit
            d_jualan = df_jualan_raw[df_jualan_raw['BulanTahun'] == b_aktif][['Gred', 'Berat_kg', 'Harga_RM_per_MT']]
            d_kos = df_kos_raw[df_kos_raw['BulanTahun'] == b_aktif][['JenisKos', 'Jumlah_RM']]
            
            st.warning(f"Mengedit: **{b_aktif}**")
            with st.form("form_edit"):
                st.subheader("Jualan")
                e_jualan = st.data_editor(d_jualan, num_rows="dynamic", key="ed_j")
                st.subheader("Kos")
                e_kos = st.data_editor(d_kos, num_rows="dynamic", key="ed_k")
                
                if st.form_submit_button("Simpan Perubahan"):
                    try:
                        supabase.table('rekod_gaji').delete().eq('BulanTahun', b_aktif).execute()
                        supabase.table('rekod_jualan').delete().eq('BulanTahun', b_aktif).execute()
                        supabase.table('rekod_kos').delete().eq('BulanTahun', b_aktif).execute()
                        
                        kos_baru = 0.0
                        if not e_kos.empty and e_kos['Jumlah_RM'].sum() > 0:
                            l_kos = e_kos[e_kos['Jumlah_RM'] > 0].to_dict('records')
                            for k in l_kos: k['BulanTahun'] = b_aktif
                            supabase.table('rekod_kos').insert(l_kos).execute()
                            kos_baru = sum(k['Jumlah_RM'] for k in l_kos)
                        
                        if not e_jualan.empty and e_jualan['Berat_kg'].sum() > 0:
                            l_resit = e_jualan[e_jualan['Berat_kg'] > 0].to_dict('records')
                            for i, r in enumerate(l_resit):
                                r['Hasil_RM'] = (r['Berat_kg']/1000)*r['Harga_RM_per_MT']
                                r['BulanTahun'] = b_aktif
                                r['IDResit'] = i+1
                            
                            k_baru = kira_payroll(l_resit, kos_baru)
                            d_gaji = {
                                'BulanTahun': b_aktif, 'JumlahJualan_RM': k_baru['jumlah_hasil_jualan'],
                                'JumlahBerat_kg': k_baru['jumlah_berat_kg'], 'GajiLori_RM': k_baru['gaji_lori'],
                                'GajiPenumbak_RM': k_baru['gaji_penumbak'], 'BahagianPemilik_RM': k_baru['bahagian_pemilik'],
                                'total_kos_operasi': k_baru['total_kos_operasi']
                            }
                            d_jual = [{'BulanTahun': r['BulanTahun'], 'IDResit': r['IDResit'], 'Gred': r['Gred'], 'Berat_kg': r['Berat_kg'], 'Harga_RM_per_MT': r['Harga_RM_per_MT'], 'Hasil_RM': r['Hasil_RM']} for r in l_resit]
                            
                            supabase.table('rekod_gaji').insert(d_gaji).execute()
                            supabase.table('rekod_jualan').insert(d_jual).execute()
                        
                        st.cache_data.clear()
                        st.session_state.bulan_edit = None
                        st.success("Data dikemaskini!")
                        st.rerun()
                    except Exception as e: st.error(f"RALAT: {e}")

        st.divider()
        
        # BAHAGIAN 3 (DELETE)
        st.subheader("❌ 3. Padam Data Bulanan")
        with st.form("del_form"):
            b_del = st.selectbox("Pilih Bulan:", senarai_bulan_rekod, key="del_sel")
            confirm = st.checkbox("Saya faham.")
            if st.form_submit_button("Padam Kekal"):
                if confirm:
                    try:
                        supabase.table('rekod_gaji').delete().eq('BulanTahun', b_del).execute()
                        supabase.table('rekod_jualan').delete().eq('BulanTahun', b_del).execute()
                        supabase.table('rekod_kos').delete().eq('BulanTahun', b_del).execute()
                        st.cache_data.clear()
                        st.success("Terpadam.")
                        st.rerun()
                    except Exception as e: st.error(f"RALAT: {e}")
                else: st.error("Sila sahkan.")

        st.divider()

        # BAHAGIAN 4 (BACKUP)
        st.subheader("🗄️ 4. Backup Excel")
        st.info("Muat turun semua data.")
        excel_data = to_excel(
            df_gaji_raw.drop(columns=['id', 'created_at'], errors='ignore'),
            df_jualan_raw.drop(columns=['id', 'created_at'], errors='ignore'),
            df_kos_raw.drop(columns=['id', 'created_at'], errors='ignore')
        )
        t_back = datetime.date.today().strftime("%Y-%m-%d")
        st.download_button("Muat Turun Excel", excel_data, f"backup_{t_back}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==============================================================================
# HALAMAN 4: LAPORAN BERKELOMPOK
# ==============================================================================
elif page == "📈 Laporan Berkelompok":
    st.header("📈 Laporan Berkelompok")
    
    if df_gaji_processed.empty:
        st.warning("Tiada data.")
    else:
        years = sorted(df_gaji_processed['Tahun'].unique(), reverse=True)
        with st.form("form_report"):
            y = st.selectbox("Tahun:", years)
            t = st.radio("Jenis:", ["Separuh Tahun Pertama (Jan-Jun)", "Separuh Tahun Kedua (Jul-Dis)", "Laporan Tahunan Penuh (Jan-Dec)"])
            if st.form_submit_button("Jana PDF"):
                h1 = ["Januari", "Februari", "Mac", "April", "Mei", "Jun"]
                h2 = ["Julai", "Ogos", "September", "Oktober", "November", "Disember"]
                
                if "Pertama" in t:
                    lst = [f"{b} {y}" for b in h1]
                    ttl = f"Separuh Tahun Pertama {y}"
                elif "Kedua" in t:
                    lst = [f"{b} {y}" for b in h2]
                    ttl = f"Separuh Tahun Kedua {y}"
                else:
                    lst = [f"{b} {y}" for b in (h1+h2)]
                    ttl = f"Tahunan Penuh {y}"

                d_g = df_gaji_raw[df_gaji_raw['BulanTahun'].isin(lst)]
                d_j = df_jualan_raw[df_jualan_raw['BulanTahun'].isin(lst)]
                d_k = df_kos_raw[df_kos_raw['BulanTahun'].isin(lst)]

                if d_g.empty: st.error("Tiada data.")
                else:
                    pdf = jana_pdf_berkelompok(ttl, d_g, d_j, d_k)
                    st.download_button(f"Muat Turun {ttl}", pdf, f"Laporan_{ttl.replace(' ', '_')}.pdf", "application/pdf")

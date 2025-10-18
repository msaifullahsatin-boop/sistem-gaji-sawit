# Nama fail: app.py
import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import io
import plotly.express as px
from supabase import create_client, Client

# --- FUNGSI-FUNGSI LOGIK (Tiada Perubahan) ---
def kira_payroll(senarai_resit):
    KADAR_LORI_PER_KG = 0.07
    jumlah_hasil_jualan = sum(resit['Hasil_RM'] for resit in senarai_resit)
    jumlah_berat_kg = sum(resit['Berat_kg'] for resit in senarai_resit)
    gaji_lori = jumlah_berat_kg * KADAR_LORI_PER_KG
    baki_bersih = jumlah_hasil_jualan - gaji_lori
    gaji_penumbak = baki_bersih / 2
    bahagian_pemilik = baki_bersih / 2
    data_kiraan = {
        "jumlah_hasil_jualan": jumlah_hasil_jualan,
        "jumlah_berat_kg": jumlah_berat_kg,
        "jumlah_berat_mt": jumlah_berat_kg / 1000,
        "gaji_lori": gaji_lori,
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
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "Bahagian 1: Butiran Jualan (Resit)", ln=True)
    pdf.set_font("Helvetica", size=11)
    for i, resit in enumerate(senarai_resit):
        teks_resit = f"  Resit #{i+1} (Gred {resit['Gred']}): {resit['Berat_kg']:.2f} kg @ RM{resit['Harga_RM_per_MT']:.2f}/MT = RM{resit['Hasil_RM']:.2f}"
        pdf.cell(0, 8, teks_resit, ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 8, f"Jumlah Berat Keseluruhan: {data_kiraan['jumlah_berat_kg']:.2f} kg", ln=True)
    pdf.cell(0, 8, f"Jumlah Hasil Jualan Kasar: RM{data_kiraan['jumlah_hasil_jualan']:.2f}", ln=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "Bahagian 2: Pengiraan Gaji dan Pembahagian", ln=True)
    pdf.set_font("Helvetica", 'BU', 11)
    pdf.cell(0, 8, "Gaji Pekerja 1 (Lori):", ln=True)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"  Kiraan: {data_kiraan['jumlah_berat_kg']:.2f} kg x RM{data_kiraan['kadar_lori_per_kg']:.2f}/kg", ln=True)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 8, f"  Jumlah Gaji Lori = RM{data_kiraan['gaji_lori']:.2f}", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", 'BU', 11)
    pdf.cell(0, 8, "Hasil Bersih (Selepas Tolak Gaji Lori):", ln=True)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"  Kiraan: RM{data_kiraan['jumlah_hasil_jualan']:.2f} - RM{data_kiraan['gaji_lori']:.2f}", ln=True)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 8, f"  Hasil Bersih = RM{data_kiraan['baki_bersih']:.2f}", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", 'BU', 11)
    pdf.cell(0, 8, "Pembahagian Hasil Bersih (50/50):", ln=True)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"  Kiraan: RM{data_kiraan['baki_bersih']:.2f} / 2", ln=True)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 8, f"  Gaji Pekerja 2 (Penumbak) = RM{data_kiraan['gaji_penumbak']:.2f}", ln=True)
    pdf.cell(0, 8, f"  Bahagian Pemilik Ladang = RM{data_kiraan['bahagian_pemilik']:.2f}", ln=True)
    pdf.ln(15)
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

# --- FUNGSI UTAMA APLIKASI WEB ---
# ----------------------------------
st.set_page_config(layout="wide", page_title="Sistem Gaji Sawit")

# --- 1. BAHAGIAN LOG MASUK & KESELAMATAN (TELAH DIUBAH SUAI) ---
def check_password():
    """Returns True if user has entered the correct password."""
    
    if "logged_in" in st.session_state and st.session_state["logged_in"] == True:
        return True

    try:
        # Cuba akses kunci seperti biasa
        correct_password = st.secrets["APP_PASSWORD"]
        
    except KeyError:
        # --- BLOK DEBUG ---
        # JIKA GAGAL, ini bermakna kunci itu tiada.
        st.error("RALAT: Kunci 'APP_PASSWORD' tidak ditemui dalam Secrets!")
        st.subheader("Mod Debug: Kunci 'Secrets' Yang Dikesan")
        
        try:
            # st.secrets berkelakuan seperti 'dictionary'. Mari kita lihat semua kuncinya.
            available_keys = list(st.secrets.keys())
            st.write("Senarai kunci yang wujud:")
            st.write(available_keys)
            
            if "supabase" in available_keys:
                st.write("Kunci di dalam 'supabase':")
                st.write(list(st.secrets["supabase"].keys()))
            
            st.warning("PENTING: Pastikan 'APP_PASSWORD' (huruf besar) wujud dalam senarai 'Secrets' anda dan TIDAK berada di dalam 'supabase'.")
        
        except Exception as e:
            st.error(f"Ralat tambahan semasa cuba menyenaraikan kunci: {e}")
            
        return False # Hentikan fungsi di sini
        # --- TAMAT BLOK DEBUG ---
        
    except Exception as e:
        # Tangkap ralat lain
        st.error(f"Ralat tidak dijangka semasa membaca 'secrets': {e}")
        return False

    # --- BORANG LOG MASUK (jika kunci wujud) ---
    st.warning("🔒 Sila masukkan kata laluan untuk mengakses aplikasi ini.")
    password = st.text_input("Kata Laluan:", type="password")

    if st.button("Log Masuk"):
        if password == correct_password:
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Kata laluan salah.")
    
    return False

# --- PANGGIL FUNGSI LOG MASUK DI SINI ---
if not check_password():
    st.stop() # Hentikan aplikasi jika log masuk gagal

# --- 2. SAMBUNGAN KE SUPABASE ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Ralat menyambung ke Supabase. Pastikan 'secrets' [supabase] anda betul.")
    st.exception(e)
    st.stop()

# --- 3. MUATKAN DATA DARI SUPABASE ---
@st.cache_data(ttl=600)
def muat_data():
    try:
        response_gaji = supabase.table('rekod_gaji').select("*").order('id', desc=False).execute()
        df_gaji = pd.DataFrame(response_gaji.data)
        response_jualan = supabase.table('rekod_jualan').select("*").order('id', desc=False).execute()
        df_jualan = pd.DataFrame(response_jualan.data)
        return df_gaji, df_jualan
    except Exception as e:
        st.error(f"Ralat membaca data dari Supabase: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_gaji, df_jualan = muat_data()

# --- 4. PAPARAN APLIKASI SELEPAS LOG MASUK ---
st.title("Sistem Pengurusan Ladang Sawit 🧑‍🌾")

st.sidebar.title("Navigasi")
page = st.sidebar.radio("Pilih Halaman:", ["📊 Dashboard Statistik", "📝 Kemasukan Data Baru"])

if st.sidebar.button("Segarkan Semula Data (Refresh)"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.error("Klik untuk keluar dari sistem.")
if st.sidebar.button("Log Keluar"):
    st.session_state["logged_in"] = False
    st.rerun()


# --- Halaman 1: Dashboard Statistik ---
if page == "📊 Dashboard Statistik":
    st.header("📊 Dashboard Statistik")
    
    if not df_gaji.empty:
        df_gaji_paparan = df_gaji.drop(columns=['id', 'created_at'], errors='ignore')
    else:
        df_gaji_paparan = df_gaji
        
    if not df_jualan.empty:
        df_jualan_paparan = df_jualan.drop(columns=['id', 'created_at'], errors='ignore')
    else:
        df_jualan_paparan = df_jualan
    
    if df_gaji_paparan.empty:
        st.warning("Tiada data untuk dipaparkan. Sila ke halaman 'Kemasukan Data Baru' untuk menambah data.")
    else:
        # KPI Utama
        total_sales = df_gaji_paparan['JumlahJualan_RM'].sum()
        total_weight_kg = df_gaji_paparan['JumlahBerat_kg'].sum()
        avg_monthly_owner = df_gaji_paparan['BahagianPemilik_RM'].mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("Jumlah Jualan Keseluruhan", f"RM{total_sales:,.2f}")
        col2.metric("Jumlah Berat Keseluruhan", f"{total_weight_kg:,.0f} kg")
        col3.metric("Purata Pendapatan Bulanan (Pemilik)", f"RM{avg_monthly_owner:,.2f}")
        
        st.markdown("---")
        
        # Graf Tren
        st.subheader("Tren Jualan dan Pembahagian Gaji")
        df_gaji_sorted = df_gaji_paparan.copy()
        try:
            df_gaji_sorted['TarikhSort'] = pd.to_datetime(df_gaji_sorted['BulanTahun'], format='%B %Y', errors='coerce')
            if df_gazi_sorted['TarikhSort'].isnull().all(): 
                df_gazi_sorted['TarikhSort'] = pd.to_datetime(df_gazi_sorted['BulanTahun'], errors='coerce')
            df_gazi_sorted = df_gazi_sorted.sort_values('TarikhSort')
        except Exception:
            pass 
            
        fig_tren_gaji = px.line(
            df_gazi_sorted, 
            x='BulanTahun', 
            y=['JumlahJualan_RM', 'GajiLori_RM', 'GajiPenumbak_RM', 'BahagianPemilik_RM'],
            title="Perbandingan Jualan Kasar vs Pembahagian Gaji",
            labels={'value': 'Jumlah (RM)', 'BulanTahun': 'Bulan'},
            markers=True
        )
        st.plotly_chart(fig_tren_gaji, use_container_width=True)
        
        # Analisis Gred
        st.subheader("Analisis Mengikut Gred")
        col_gred1, col_gred2 = st.columns(2)
        fig_pie_hasil = px.pie(
            df_jualan_paparan, names='Gred', values='Hasil_RM', 
            title="Pecahan Hasil Jualan (RM) mengikut Gred"
        )
        col_gred1.plotly_chart(fig_pie_hasil, use_container_width=True)
        
        fig_pie_berat = px.pie(
            df_jualan_paparan, names='Gred', values='Berat_kg', 
            title="Pecahan Berat Jualan (kg) mengikut Gred"
        )
        col_gred2.plotly_chart(fig_pie_berat, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Data Mentah (dari Database)")
        st.dataframe(df_gaji_paparan)
        st.dataframe(df_jualan_paparan)

# --- Halaman 2: Kemasukan Data Baru ---
elif page == "📝 Kemasukan Data Baru":
    st.header("📝 Kemasukan Data Jualan Bulanan Baru")
    
    with st.form("borang_data_baru"):
        
        st.subheader("1. Maklumat Asas")
        col1, col2 = st.columns(2)
        senarai_bulan = ["Januari", "Februari", "Mac", "April", "Mei", "Jun", 
                        "Julai", "Ogos", "September", "Oktober", "November", "Disember"]
        tahun_semasa = datetime.date.today().year
        senarai_tahun = list(range(tahun_semasa - 5, tahun_semasa + 2)) 
        senarai_tahun.reverse()
        with col1:
            bulan = st.selectbox("Pilih Bulan:", senarai_bulan, index=datetime.date.today().month - 1) 
        with col2:
            tahun = st.selectbox("Pilih Tahun:", senarai_tahun)
        bulan_tahun = f"{bulan} {tahun}"
        st.info(f"Anda sedang memasukkan data untuk: **{bulan_tahun}**")
        
        st.subheader("2. Butiran Resit Jualan")
        st.info("Gunakan editor di bawah untuk memasukkan semua resit anda. Klik baris akhir dan tekan 'Enter' atau klik ikon '+' untuk menambah baris (resit) baru.")
        df_resit_input = pd.DataFrame(
            [
                {"Gred": "A", "Berat_kg": 0.0, "Harga_RM_per_MT": 0.0},
                {"Gred": "B", "Berat_kg": 0.0, "Harga_RM_per_MT": 0.0},
                {"Gred": "C", "Berat_kg": 0.0, "Harga_RM_per_MT": 0.0},
            ]
        )
        edited_df = st.data_editor(
            df_resit_input,
            num_rows="dynamic",
            column_config={
                "Gred": st.column_config.SelectboxColumn("Gred", options=["A", "B", "C"], required=True),
                "Berat_kg": st.column_config.NumberColumn("Berat (kg)", min_value=0.0, format="%.2f", required=True),
                "Harga_RM_per_MT": st.column_config.NumberColumn("Harga Jualan (RM/MT)", min_value=0.0, format="%.2f", required=True)
            },
            key="data_editor"
        )
        
        submit_button = st.form_submit_button(label="Kira, Jana PDF & Simpan ke Database")

    # --- Logik Selepas Borang Dihantar ---
    if submit_button:
        # Semakan keselamatan
        if not bulan_tahun:
            st.error("Ralat: Sila pilih Bulan dan Tahun.")
        elif edited_df['Berat_kg'].sum() == 0:
            st.error("Ralat: Sila masukkan sekurang-kurangnya satu resit jualan dengan berat lebih dari 0.")
        # Semak jika data bulan itu sudah wujud
        elif not df_gaji.empty and bulan_tahun in df_gaji['BulanTahun'].values:
            st.error(f"Ralat: Data untuk {bulan_tahun} sudah wujud dalam database. Sila semak semula.")
        else:
            with st.spinner("Sedang mengira dan menyimpan..."):
                
                # 1. Bersihkan data resit
                senarai_resit = edited_df[edited_df['Berat_kg'] > 0].to_dict('records')
                
                # 2. Kira hasil untuk setiap resit
                for i, resit in enumerate(senarai_resit):
                    resit['Hasil_RM'] = (resit['Berat_kg'] / 1000) * resit['Harga_RM_per_MT']
                    resit['BulanTahun'] = bulan_tahun
                    resit['IDResit'] = i + 1

                # 3. Lakukan kiraan gaji
                data_kiraan = kira_payroll(senarai_resit)
                
                # 4. Jana PDF (dalam ingatan)
                pdf_binary = jana_pdf_binary(bulan_tahun, senarai_resit, data_kiraan)
                
                # 5. Sediakan data baru untuk dihantar ke Supabase
                data_gaji_baru_dict = {
                    'BulanTahun': bulan_tahun,
                    'JumlahJualan_RM': data_kiraan['jumlah_hasil_jualan'],
                    'JumlahBerat_kg': data_kiraan['jumlah_berat_kg'],
                    'GajiLori_RM': data_kiraan['gaji_lori'],
                    'GajiPenumbak_RM': data_kiraan['gaji_penumbak'],
                    'BahagianPemilik_RM': data_kiraan['bahagian_pemilik']
                }
                
                data_jualan_baru_list = [
                    {
                        'BulanTahun': resit['BulanTahun'],
                        'IDResit': resit['IDResit'],
                        'Gred': resit['Gred'],
                        'Berat_kg': resit['Berat_kg'],
                        'Harga_RM_per_MT': resit['Harga_RM_per_MT'],
                        'Hasil_RM': resit['Hasil_RM']
                    } for resit in senarai_resit
                ]
                
                # 6. Hantar data ke Supabase
                try:
                    supabase.table('rekod_gaji').insert(data_gaji_baru_dict).execute()
                    supabase.table('rekod_jualan').insert(data_jualan_baru_list).execute()
                    st.cache_data.clear()

                except Exception as e:
                    st.error(f"RALAT: Gagal menyimpan data ke Supabase. {e}")
                    st.stop()

                # 7. Papar rumusan & butang muat turun
                st.success(f"Data untuk {bulan_tahun} telah berjaya diproses DAN DISIMPAN ke database!")
                st.subheader("Rumusan Kiraan")
                st.metric("Jumlah Jualan Kasar", f"RM{data_kiraan['jumlah_hasil_jualan']:.2f}")
                st.metric("Gaji Pekerja 1 (Lori)", f"RM{data_kiraan['gaji_lori']:.2f}")
                st.metric("Gaji Pekerja 2 (Penumbak)", f"RM{data_kiraan['gaji_penumbak']:.2f}")
                st.metric("Bahagian Pemilik", f"RM{data_kiraan['bahagian_pemilik']:.2f}")
                st.subheader("Muat Turun")
                nama_fail_pdf = f"Laporan_Gaji_{bulan_tahun.replace(' ', '_')}.pdf"
                st.download_button(
                    label="Muat Turun Laporan PDF",
                    data=pdf_binary,
                    file_name=nama_fail_pdf,
                    mime="application/pdf"
                )

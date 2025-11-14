# Nama fail: app.py
import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import io
import plotly.express as px
from supabase import create_client, Client

# --- FUNGSI-FUNGSI LOGIK ---

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

# --- FUNGSI UTAMA APLIKASI WEB ---
st.set_page_config(layout="wide", page_title="Sistem Gaji Sawit")

# --- 1. BAHAGIAN LOG MASUK & KESELAMATAN ---
def check_password():
    if "logged_in" in st.session_state and st.session_state["logged_in"] == True:
        return True
    try:
        correct_password = st.secrets["APP_PASSWORD"]
    except KeyError:
        st.error("Ralat: Rahsia 'APP_PASSWORD' tidak ditemui. Pastikan ia ditambah ke 'Secrets' di Streamlit Cloud.")
        return False
    except Exception as e:
        st.error(f"Ralat 'secrets' tidak dijangka: {e}")
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

if not check_password():
    st.stop()

# --- 2. SAMBUNGAN KE SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except KeyError:
    st.error("Ralat: Rahsia 'SUPABASE_URL' atau 'SUPABASE_KEY' tidak ditemui.")
    st.stop()
except Exception as e:
    st.error("Ralat menyambung ke Supabase.")
    st.exception(e)
    st.stop()

# --- 3. MUATKAN DATA DARI SUPABASE (TELAH DIBAIKI) ---
@st.cache_data(ttl=600)
def muat_data():
    try:
        response_gaji = supabase.table('rekod_gaji').select("*").order('id', desc=False).execute()
        df_gaji = pd.DataFrame(response_gaji.data)
        
        response_jualan = supabase.table('rekod_jualan').select("*").order('id', desc=False).execute()
        df_jualan = pd.DataFrame(response_jualan.data)
        
        response_kos = supabase.table('rekod_kos').select("*").order('id', desc=False).execute()
        df_kos = pd.DataFrame(response_kos.data)
        
        # --- PENAMBAHBAIKAN BERMULA DI SINI ---
        # Tentukan nama kolum yang sepatutnya wujud, walaupun table kosong
        expected_gaji_cols = ['BulanTahun', 'JumlahJualan_RM', 'JumlahBerat_kg', 'GajiLori_RM', 
                              'GajiPenumbak_RM', 'BahagianPemilik_RM', 'total_kos_operasi', 
                              'id', 'created_at']
        expected_jualan_cols = ['BulanTahun', 'IDResit', 'Gred', 'Berat_kg', 
                                'Harga_RM_per_MT', 'Hasil_RM', 'id', 'created_at']
        expected_kos_cols = ['BulanTahun', 'JenisKos', 'Jumlah_RM', 'id', 'created_at']

        # Jika df_gaji kosong, cipta semula dengan kolum yang betul
        if df_gaji.empty:
            df_gaji = pd.DataFrame(columns=[col for col in expected_gaji_cols if col in supabase.table('rekod_gaji').select('BulanTahun').execute().data or col in ['id', 'created_at']]) # Logik mudah
            # Cara lebih selamat jika table wujud tapi kosong:
            df_gaji = pd.DataFrame(columns=expected_gaji_cols)
        
        # Jika df_jualan kosong, cipta semula dengan kolum yang betul
        if df_jualan.empty:
            df_jualan = pd.DataFrame(columns=expected_jualan_cols)

        # Jika df_kos kosong, cipta semula dengan kolum yang betul (INI YANG PALING PENTING UNTUK RALAT ANDA)
        if df_kos.empty:
            df_kos = pd.DataFrame(columns=expected_kos_cols)
        # --- PENAMBAHBAIKAN TAMAT ---

        return df_gaji, df_jualan, df_kos
    
    except Exception as e:
        st.error(f"Ralat membaca data dari Supabase: {e}")
        # Pulangkan DataFrame kosong dengan kolum yang betul jika ralat
        return (pd.DataFrame(columns=expected_gaji_cols), 
                pd.DataFrame(columns=expected_jualan_cols), 
                pd.DataFrame(columns=expected_kos_cols))

df_gaji, df_jualan, df_kos = muat_data()

# --- 4. PAPARAN APLIKASI SELEPAS LOG MASUK ---
st.title("Sistem Pengurusan Ladang Sawit 🧑‍🌾")

st.sidebar.title("Navigasi")
page = st.sidebar.radio("Pilih Halaman:", ["📊 Dashboard Statistik", "📝 Kemasukan Data Baru", "🖨️ Urus & Cetak Semula"])

if st.sidebar.button("Segarkan Semula Data (Refresh)"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.error("Klik untuk keluar dari sistem.")
if st.sidebar.button("Log Masuk Semula"):
    st.session_state["logged_in"] = False
    st.rerun()


# --- Halaman 1: Dashboard Statistik ---
if page == "📊 Dashboard Statistik":
    st.header("📊 Dashboard Statistik")
    
    df_gaji_paparan = df_gaji.drop(columns=['id', 'created_at'], errors='ignore') if not df_gaji.empty else df_gaji
    df_jualan_paparan = df_jualan.drop(columns=['id', 'created_at'], errors='ignore') if not df_jualan.empty else df_jualan
    df_kos_paparan = df_kos.drop(columns=['id', 'created_at'], errors='ignore') if not df_kos.empty else df_kos
    
    if df_gaji_paparan.empty:
        st.warning("Tiada data untuk dipaparkan. Sila ke halaman 'Kemasukan Data Baru' untuk menambah data.")
    else:
        # KPI
        total_sales = df_gaji_paparan['JumlahJualan_RM'].sum()
        total_weight_kg = df_gaji_paparan['JumlahBerat_kg'].sum()
        avg_monthly_owner = df_gaji_paparan['BahagianPemilik_RM'].mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("Jumlah Jualan Keseluruhan", f"RM{total_sales:,.2f}")
        col2.metric("Jumlah Berat Keseluruhan", f"{total_weight_kg:,.0f} kg")
        col3.metric("Purata Pendapatan Bulanan (Pemilik)", f"RM{avg_monthly_owner:,.2f}")
        st.markdown("---")
        
        # Graf Tren
        st.subheader("Tren Jualan, Kos, dan Pembahagian Gaji")
        df_gaji_sorted = df_gaji_paparan.copy()
        
        if 'total_kos_operasi' not in df_gaji_sorted.columns:
            df_gaji_sorted['total_kos_operasi'] = 0.0
        
        try:
            # Blok Pengisihan Graf
            peta_bulan = {
                "Januari": 1, "Februari": 2, "Mac": 3, "April": 4, "Mei": 5, "Jun": 6,
                "Julai": 7, "Ogos": 8, "September": 9, "Oktober": 10, "November": 11, "Disember": 12
            }
            df_split = df_gaji_sorted['BulanTahun'].str.split(' ', expand=True)
            df_gaji_sorted['BulanString'] = df_split[0]
            df_gaji_sorted['Tahun'] = df_split[1].astype(int)
            df_gaji_sorted['BulanNombor'] = df_gaji_sorted['BulanString'].map(peta_bulan)
            df_gaji_sorted = df_gaji_sorted.sort_values(by=['Tahun', 'BulanNombor'])
            
        except Exception as e:
            st.warning(f"Ralat semasa mengisih graf: {e}. Graf mungkin tidak teratur.")
            pass 
            
        fig_tren_gaji = px.line(
            df_gaji_sorted, 
            x='BulanTahun', 
            y=['JumlahJualan_RM', 'total_kos_operasi', 'GajiLori_RM', 'GajiPenumbak_RM', 'BahagianPemilik_RM'],
            title="Perbandingan Jualan, Kos, dan Pembahagian Gaji",
            labels={'value': 'Jumlah (RM)', 'BulanTahun': 'Bulan'},
            markers=True
        )
        st.plotly_chart(fig_tren_gaji, use_container_width=True)
        
        # Analisis Pecahan
        st.subheader("Analisis Pecahan")
        col_gred1, col_gred2 = st.columns(2)
        
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
        st.dataframe(df_gaji_paparan)
        st.write("Data Jualan (Butiran Resit)")
        st.dataframe(df_jualan_paparan)
        st.write("Data Kos Operasi")
        st.dataframe(df_kos_paparan)

# --- Halaman 2: Kemasukan Data Baru ---
elif page == "📝 Kemasukan Data Baru":
    st.header("📝 Kemasukan Data Jualan Bulanan Baru")
    
    tab_jualan, tab_kos = st.tabs(["1. Masukkan Jualan (Gaji)", "2. Masukkan Kos Operasi"])

    # --- TAB 1: Borang Jualan dan Gaji ---
    with tab_jualan:
        st.subheader("Borang Kiraan Gaji")
        with st.form("borang_data_gaji"):
            
            st.subheader("A. Maklumat Asas")
            col1, col2 = st.columns(2)
            senarai_bulan = ["Januari", "Februari", "Mac", "April", "Mei", "Jun", 
                            "Julai", "Ogos", "September", "Oktober", "November", "Disember"]
            tahun_semasa = datetime.date.today().year
            senarai_tahun = list(range(tahun_semasa - 5, tahun_semasa + 2)) 
            senarai_tahun.reverse()
            with col1:
                bulan_gaji = st.selectbox("Pilih Bulan:", senarai_bulan, index=datetime.date.today().month - 1, key="bulan_gaji") 
            with col2:
                tahun_gaji = st.selectbox("Pilih Tahun:", senarai_tahun, key="tahun_gaji")
            bulan_tahun_gaji = f"{bulan_gaji} {tahun_gaji}"
            st.info(f"Anda sedang mengira gaji untuk: **{bulan_tahun_gaji}**")
            
            st.subheader("B. Butiran Resit Jualan")
            st.info("Masukkan semua resit jualan untuk bulan ini.")
            df_resit_input = pd.DataFrame(
                [
                    {"Gred": "A", "Berat_kg": 0.0, "Harga_RM_per_MT": 0.0},
                    {"Gred": "B", "Berat_kg": 0.0, "Harga_RM_per_MT": 0.0},
                    {"Gred": "C", "Berat_kg": 0.0, "Harga_RM_per_MT": 0.0},
                ]
            )
            edited_df_jualan = st.data_editor(
                df_resit_input, num_rows="dynamic",
                column_config={
                    "Gred": st.column_config.SelectboxColumn("Gred", options=["A", "B", "C"], required=True),
                    "Berat_kg": st.column_config.NumberColumn("Berat (kg)", min_value=0.0, format="%.2f", required=True),
                    "Harga_RM_per_MT": st.column_config.NumberColumn("Harga Jualan (RM/MT)", min_value=0.0, format="%.2f", required=True)
                },
                key="data_editor_jualan"
            )
            
            st.subheader("C. Dapatkan Kos Operasi")
            st.info(f"Sistem akan mengambil jumlah kos operasi yang telah anda masukkan untuk bulan **{bulan_tahun_gaji}**.")
            
            submit_button_gaji = st.form_submit_button(label="Kira, Jana PDF & Simpan Gaji")

    # --- TAB 2: Borang Kos Operasi ---
    with tab_kos:
        st.subheader("Borang Kemasukan Kos Operasi")
        st.info("Masukkan kos seperti baja, racun, minyak, dll. Anda boleh masukkan kos ini bila-bila masa.")
        
        with st.form("borang_data_kos"):
            st.subheader("A. Maklumat Asas")
            col1_kos, col2_kos = st.columns(2)
            with col1_kos:
                bulan_kos = st.selectbox("Pilih Bulan:", senarai_bulan, index=datetime.date.today().month - 1, key="bulan_kos") 
            with col2_kos:
                tahun_kos = st.selectbox("Pilih Tahun:", senarai_tahun, key="tahun_kos")
            bulan_tahun_kos = f"{bulan_kos} {tahun_kos}"
            st.info(f"Anda sedang memasukkan kos untuk: **{bulan_tahun_kos}**")
            
            st.subheader("B. Butiran Kos")
            df_kos_input = pd.DataFrame(
                [
                    {"JenisKos": "Baja", "Jumlah_RM": 0.0},
                    {"JenisKos": "Racun", "Jumlah_RM": 0.0},
                ]
            )
            edited_df_kos = st.data_editor(
                df_kos_input, num_rows="dynamic",
                column_config={
                    "JenisKos": st.column_config.TextColumn("Jenis Kos", required=True),
                    "Jumlah_RM": st.column_config.NumberColumn("Jumlah (RM)", min_value=0.0, format="%.2f", required=True)
                },
                key="data_editor_kos"
            )
            
            submit_button_kos = st.form_submit_button(label="Simpan Kos ke Database")

    # --- Logik Selepas Borang KOS Dihantar ---
    if submit_button_kos:
        if edited_df_kos['Jumlah_RM'].sum() == 0:
            st.error("Ralat: Sila masukkan sekurang-kurangnya satu kos dengan jumlah lebih dari 0.")
        else:
            with st.spinner("Menyimpan kos..."):
                senarai_kos_bersih = edited_df_kos[edited_df_kos['Jumlah_RM'] > 0].to_dict('records')
                
                for kos in senarai_kos_bersih:
                    kos['BulanTahun'] = bulan_tahun_kos
                
                try:
                    # Semak jika data kos untuk bulan ini sudah wujud
                    if not df_kos.empty and bulan_tahun_kos in df_kos['BulanTahun'].values:
                        # Jika wujud, padam yang lama dahulu
                        supabase.table('rekod_kos').delete().eq('BulanTahun', bulan_tahun_kos).execute()
                    
                    # Masukkan data kos baru
                    supabase.table('rekod_kos').insert(senarai_kos_bersih).execute()
                    st.cache_data.clear()
                    st.success(f"Data kos untuk {bulan_tahun_kos} telah berjaya disimpan/dikemaskini!")
                except Exception as e:
                    st.error(f"RALAT: Gagal menyimpan data kos. {e}")
                    
    # --- Logik Selepas Borang GAJI Dihantar ---
    if submit_button_gaji:
        if not bulan_tahun_gaji:
            st.error("Ralat: Sila pilih Bulan dan Tahun.")
        elif edited_df_jualan['Berat_kg'].sum() == 0:
            st.error("Ralat: Sila masukkan sekurang-kurangnya satu resit jualan.")
        elif not df_gaji.empty and bulan_tahun_gaji in df_gaji['BulanTahun'].values:
            st.error(f"Ralat: Data gaji untuk {bulan_tahun_gaji} sudah wujud.")
        else:
            with st.spinner("Sedang mengira dan menyimpan..."):
                
                # 1. Dapatkan kos
                if not df_kos.empty:
                    kos_bulan_ini = df_kos[df_kos['BulanTahun'] == bulan_tahun_gaji]['Jumlah_RM'].sum()
                else:
                    kos_bulan_ini = 0.0
                
                # 2. Resit jualan
                senarai_resit = edited_df_jualan[edited_df_jualan['Berat_kg'] > 0].to_dict('records')
                
                # 3. Kira hasil
                for i, resit in enumerate(senarai_resit):
                    resit['Hasil_RM'] = (resit['Berat_kg'] / 1000) * resit['Harga_RM_per_MT']
                    resit['BulanTahun'] = bulan_tahun_gaji
                    resit['IDResit'] = i + 1

                # 4. Kira gaji
                data_kiraan = kira_payroll(senarai_resit, kos_bulan_ini)
                
                # 5. Jana PDF
                pdf_binary = jana_pdf_binary(bulan_tahun_gaji, senarai_resit, data_kiraan)
                
                # 6. Sediakan data untuk Supabase
                data_gaji_baru_dict = {
                    'BulanTahun': bulan_tahun_gaji,
                    'JumlahJualan_RM': data_kiraan['jumlah_hasil_jualan'],
                    'JumlahBerat_kg': data_kiraan['jumlah_berat_kg'],
                    'GajiLori_RM': data_kiraan['gaji_lori'],
                    'GajiPenumbak_RM': data_kiraan['gaji_penumbak'],
                    'BahagianPemilik_RM': data_kiraan['bahagian_pemilik'],
                    'total_kos_operasi': data_kiraan['total_kos_operasi']
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
                
                # 7. Hantar data ke Supabase
                try:
                    supabase.table('rekod_gaji').insert(data_gaji_baru_dict).execute()
                    supabase.table('rekod_jualan').insert(data_jualan_baru_list).execute()
                    st.cache_data.clear()

                except Exception as e:
                    st.error(f"RALAT: Gagal menyimpan data gaji. {e}")
                    st.stop()

                # 8. Papar rumusan
                st.success(f"Data gaji untuk {bulan_tahun_gaji} telah berjaya diproses DAN DISIMPAN!")
                
                st.subheader("Rumusan Kiraan")
                st.metric("Jumlah Jualan Kasar", f"RM{data_kiraan['jumlah_hasil_jualan']:.2f}")
                st.metric("Tolak: Gaji Lori", f"RM{data_kiraan['gaji_lori']:.2f}")
                st.metric("Tolak: Kos Operasi", f"RM{data_kiraan['total_kos_operasi']:.2f}")
                st.metric("Hasil Bersih (Untuk Dibahagi)", f"RM{data_kiraan['baki_bersih']:.2f}", delta_color="off")
                
                col1_final, col2_final = st.columns(2)
                col1_final.metric("Gaji Pekerja 2 (Penumbak)", f"RM{data_kiraan['gaji_penumbak']:.2f}")
                col2_final.metric("Bahagian Pemilik", f"RM{data_kiraan['bahagian_pemilik']:.2f}")

                st.subheader("Muat Turun")
                nama_fail_pdf = f"Laporan_Gaji_{bulan_tahun_gaji.replace(' ', '_')}.pdf"
                st.download_button(
                    label="Muat Turun Laporan PDF",
                    data=pdf_binary,
                    file_name=nama_fail_pdf,
                    mime="application/pdf"
                )

# --- Halaman 3: Urus & Cetak Semula ---
elif page == "🖨️ Urus & Cetak Semula":
    st.header("🖨️ Urus & Cetak Semula Laporan")
    
    if df_gaji.empty:
        st.info("Tiada data untuk diurus atau dicetak.")
    else:
        # Dapatkan senarai bulan yang unik dari data gaji
        senarai_bulan_rekod = df_gaji['BulanTahun'].unique()
        
        # --- BAHAGIAN 1: CETAK SEMULA PDF ---
        st.subheader("1. Cetak Semula Laporan PDF Bulanan")
        with st.form("borang_cetak_semula"):
            bulan_cetak = st.selectbox("Pilih Bulan untuk Dicetak:", senarai_bulan_rekod)
            submit_cetak = st.form_submit_button("Jana PDF")

        if submit_cetak:
            with st.spinner(f"Menjana PDF untuk {bulan_cetak}..."):
                # Dapatkan data untuk bulan yang dipilih
                data_gaji_bulan_ini = df_gaji[df_gaji['BulanTahun'] == bulan_cetak].to_dict('records')[0]
                senarai_resit = df_jualan[df_jualan['BulanTahun'] == bulan_cetak].to_dict('records')
                
                data_kiraan_cetak = {
                    'jumlah_hasil_jualan': data_gaji_bulan_ini['JumlahJualan_RM'],
                    'jumlah_berat_kg': data_gaji_bulan_ini['JumlahBerat_kg'],
                    'gaji_lori': data_gaji_bulan_ini['GajiLori_RM'],
                    'total_kos_operasi': data_gaji_bulan_ini.get('total_kos_operasi', 0.0),
                    'kadar_lori_per_kg': 0.07, 
                    'baki_bersih': data_gaji_bulan_ini['GajiPenumbak_RM'] + data_gaji_bulan_ini['BahagianPemilik_RM'],
                    'gaji_penumbak': data_gaji_bulan_ini['GajiPenumbak_RM'],
                    'bahagian_pemilik': data_gaji_bulan_ini['BahagianPemilik_RM']
                }
                
                pdf_binary = jana_pdf_binary(bulan_cetak, senarai_resit, data_kiraan_cetak)
                
                nama_fail_pdf = f"Laporan_Gaji_{bulan_cetak.replace(' ', '_')}.pdf"
                st.download_button(
                    label=f"Muat Turun Laporan PDF untuk {bulan_cetak}",
                    data=pdf_binary,
                    file_name=nama_fail_pdf,
                    mime="application/pdf"
                )
        
        st.divider()
        
        # --- BAHAGIAN 2: KEMASKINI DATA (FUNGSI BARU) ---
        st.subheader("✏️ 2. Kemaskini Data Bulanan (Edit)")
        st.info("Untuk membetulkan kesilapan, pilih bulan, muatkan data, buat perubahan, dan simpan.")

        if 'bulan_untuk_diedit' not in st.session_state:
            st.session_state.bulan_untuk_diedit = None

        col1_edit, col2_edit = st.columns([3, 1])
        with col1_edit:
            bulan_edit_dipilih = st.selectbox("Pilih Bulan untuk Diedit:", senarai_bulan_rekod, key="pilih_bulan_edit")
        with col2_edit:
            st.write(" ")
            if st.button("Muatkan Data Sedia Ada"):
                st.session_state.bulan_untuk_diedit = bulan_edit_dipilih
                st.rerun()

        if st.session_state.bulan_untuk_diedit:
            
            bulan_edit_aktif = st.session_state.bulan_untuk_diedit
            
            # Sediakan data Jualan
            data_jualan_sedia_ada = df_jualan[df_jualan['BulanTahun'] == bulan_edit_aktif][['Gred', 'Berat_kg', 'Harga_RM_per_MT']]
            # Sediakan data Kos (Gunakan df_kos yang dipastikan ada kolum oleh muat_data())
            data_kos_sedia_ada = df_kos[df_kos['BulanTahun'] == bulan_edit_aktif][['JenisKos', 'Jumlah_RM']]
            
            st.warning(f"Anda sedang mengedit data untuk: **{bulan_edit_aktif}**")
            
            with st.form("borang_kemaskini_data"):
                st.subheader("A. Kemaskini Butiran Jualan")
                edited_df_jualan = st.data_editor(
                    data_jualan_sedia_ada, num_rows="dynamic",
                    column_config={
                        "Gred": st.column_config.SelectboxColumn("Gred", options=["A", "B", "C"], required=True),
                        "Berat_kg": st.column_config.NumberColumn("Berat (kg)", min_value=0.0, format="%.2f", required=True),
                        "Harga_RM_per_MT": st.column_config.NumberColumn("Harga Jualan (RM/MT)", min_value=0.0, format="%.2f", required=True)
                    },
                    key="data_editor_edit_jualan"
                )
                
                st.subheader("B. Kemaskini Butiran Kos")
                edited_df_kos = st.data_editor(
                    data_kos_sedia_ada, num_rows="dynamic",
                    column_config={
                        "JenisKos": st.column_config.TextColumn("Jenis Kos", required=True),
                        "Jumlah_RM": st.column_config.NumberColumn("Jumlah (RM)", min_value=0.0, format="%.2f", required=True)
                    },
                    key="data_editor_edit_kos"
                )
                
                submit_button_edit = st.form_submit_button("Kira Semula & Simpan Perubahan")

            if submit_button_edit:
                with st.spinner(f"Mengemaskini data untuk {bulan_edit_aktif}..."):
                    
                    try:
                        # 1. PADAM SEMUA data lama untuk bulan ini
                        supabase.table('rekod_gaji').delete().eq('BulanTahun', bulan_edit_aktif).execute()
                        supabase.table('rekod_jualan').delete().eq('BulanTahun', bulan_edit_aktif).execute()
                        supabase.table('rekod_kos').delete().eq('BulanTahun', bulan_edit_aktif).execute()
                        
                        # 2. Sediakan data KOS baru
                        total_kos_baru = 0.0
                        if not edited_df_kos.empty and edited_df_kos['Jumlah_RM'].sum() > 0:
                            senarai_kos_baru = edited_df_kos[edited_df_kos['Jumlah_RM'] > 0].to_dict('records')
                            for kos in senarai_kos_baru:
                                kos['BulanTahun'] = bulan_edit_aktif
                            
                            supabase.table('rekod_kos').insert(senarai_kos_baru).execute()
                            total_kos_baru = sum(k['Jumlah_RM'] for k in senarai_kos_baru)
                        
                        # 3. Sediakan data JUALAN baru & Kira Gaji
                        if not edited_df_jualan.empty and edited_df_jualan['Berat_kg'].sum() > 0:
                            senarai_resit_baru = edited_df_jualan[edited_df_jualan['Berat_kg'] > 0].to_dict('records')
                            
                            for i, resit in enumerate(senarai_resit_baru):
                                resit['Hasil_RM'] = (resit['Berat_kg'] / 1000) * resit['Harga_RM_per_MT']
                                resit['BulanTahun'] = bulan_edit_aktif
                                resit['IDResit'] = i + 1
                            
                            data_kiraan_baru = kira_payroll(senarai_resit_baru, total_kos_baru)
                            
                            data_gaji_baru_dict = {
                                'BulanTahun': bulan_edit_aktif,
                                'JumlahJualan_RM': data_kiraan_baru['jumlah_hasil_jualan'],
                                'JumlahBerat_kg': data_kiraan_baru['jumlah_berat_kg'],
                                'GajiLori_RM': data_kiraan_baru['gaji_lori'],
                                'GajiPenumbak_RM': data_kiraan_baru['gaji_penumbak'],
                                'BahagianPemilik_RM': data_kiraan_baru['bahagian_pemilik'],
                                'total_kos_operasi': data_kiraan_baru['total_kos_operasi']
                            }
                            
                            data_jualan_baru_list = [
                                {
                                    'BulanTahun': resit['BulanTahun'],
                                    'IDResit': resit['IDResit'],
                                    'Gred': resit['Gred'],
                                    'Berat_kg': resit['Berat_kg'],
                                    'Harga_RM_per_MT': resit['Harga_RM_per_MT'],
                                    'Hasil_RM': resit['Hasil_RM']
                                } for resit in senarai_resit_baru
                            ]
                            
                            supabase.table('rekod_gaji').insert(data_gaji_baru_dict).execute()
                            supabase.table('rekod_jualan').insert(data_jualan_baru_list).execute()
                        
                        # 4. Selesai
                        st.cache_data.clear()
                        st.session_state.bulan_untuk_diedit = None # Reset borang
                        st.success(f"Data untuk {bulan_edit_aktif} telah berjaya dikemaskini!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"RALAT: Gagal mengemaskini data. {e}")
        
        st.divider()
        
        # --- BAHAGIAN 3: PADAM DATA ---
        st.subheader("❌ 3. Padam Data Bulanan")
        st.warning("AMARAN: Tindakan ini akan memadam data secara kekal dari database.")
        
        with st.form("borang_padam_data"):
            bulan_dipilih = st.selectbox("Pilih Bulan dan Tahun untuk Dipadam:", senarai_bulan_rekod, key="padam_bulan")
            
            st.subheader("Pengesahan")
            st.info(f"Anda akan memadam SEMUA data Jualan, Kos, dan Gaji untuk **{bulan_dipilih}**.")
            pengesahan = st.checkbox("Saya faham dan ingin teruskan.")
            submit_button_padam = st.form_submit_button(label="Padam Data Bulan Ini Secara Kekal")

        if submit_button_padam:
            if not pengesahan:
                st.error("Ralat: Sila tandakan kotak pengesahan untuk meneruskan.")
            elif not bulan_dipilih:
                st.error("Ralat: Sila pilih bulan untuk dipadam.")
            else:
                with st.spinner(f"Memadam semua data untuk {bulan_dipilih}..."):
                    try:
                        supabase.table('rekod_gaji').delete().eq('BulanTahun', bulan_dipilih).execute()
                        supabase.table('rekod_jualan').delete().eq('BulanTahun', bulan_dipilih).execute()
                        supabase.table('rekod_kos').delete().eq('BulanTahun', bulan_dipilih).execute()
                        
                        st.cache_data.clear()
                        st.success(f"Semua data untuk {bulan_dipilih} telah berjaya dipadam.")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"RALAT: Gagal memadam data. {e}")

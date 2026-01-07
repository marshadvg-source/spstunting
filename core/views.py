from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.template.loader import get_template
from .models import Pasien, Konsultasi, DetailKonsultasi, Gejala, Kondisi, Aturan, PengukuranFisik, Notifikasi
from django.db.models import Count
from django.db import transaction
from collections import defaultdict
import random
from datetime import date, timedelta
from .utils import hitung_dan_simpan_zscore, buat_jadwal_notifikasi
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.forms import modelformset_factory, ModelForm
from django import forms
from io import BytesIO
from xhtml2pdf import pisa

# Helper function to check if user is staff
def is_staff(user):
    return user.is_staff

# Helper function to check if user is an expert (staff but not superuser with Pakar Diagnosa group)
def is_expert(user):
    return user.is_staff and not user.is_superuser and user.groups.filter(name='Pakar Diagnosa').exists()

# Index view - redirect authenticated users to appropriate dashboard
def home(request):
    # If user is staff, redirect to expert dashboard
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('dashboard_pakar')
    
    # If patient is logged in, redirect to patient dashboard
    if 'pasien_id' in request.session:
        return redirect('dashboard_pasien')
    
    # Otherwise, show the home page
    return render(request, 'index.html')

# Create your views here.

# PROMPT #1: Mesin Inferensi Forward Chaining Inti
def jalankan_inferensi(pasien_id, kode_gejala_input):
    """
    Implementasi Mesin Inferensi menggunakan metode Strict Equality Matching (Kecocokan Persis)
    
    Args:
        pasien_id: ID dari objek Pasien
        kode_gejala_input: List berisi kode-kode gejala (misal: ['G01', 'G04', 'G10'])
        
    Returns:
        Objek Konsultasi yang berisi hasil diagnosa
    """
    
    # Langkah 1: Inisialisasi dan Pencatatan Konsultasi
    try:
        pasien = Pasien.objects.get(id=pasien_id)
    except Pasien.DoesNotExist:
        raise ValueError("Pasien tidak ditemukan")
    
    # Buat objek Konsultasi baru
    konsultasi = Konsultasi.objects.create(pasien=pasien)
    
    # Catat semua kode_gejala_input ke dalam DetailKonsultasi
    for kode_gejala in kode_gejala_input:
        try:
            gejala = Gejala.objects.get(kodeGejala=kode_gejala)
            DetailKonsultasi.objects.create(konsultasi=konsultasi, gejala=gejala)
        except Gejala.DoesNotExist:
            # Lewati gejala yang tidak ditemukan
            continue
    
    # Inisialisasi Working Memory (WM) dengan kode_gejala_input
    working_memory = set(kode_gejala_input)
    
    # Langkah 2: Logika Strict Equality Matching (Kecocokan Persis)
    # Ambil semua objek Aturan dari database
    semua_aturan = Aturan.objects.select_related('kondisi', 'gejala').all()
    
    # Kelompokkan aturan berdasarkan pasangan kondisi dan kodeKelompokAturan
    aturan_kelompok = defaultdict(list)
    for aturan in semua_aturan:
        key = (aturan.kondisi.kodeKondisi, aturan.kodeKelompokAturan)
        aturan_kelompok[key].append(aturan)
    
    # Ulangi setiap kelompok aturan yang teridentifikasi
    diagnosis_ditemukan = None
    
    # Variabel untuk menyimpan diagnosis yang ditemukan dengan exact matching
    diagnosis_terbaik = None
    
    for (kode_kondisi, kode_kelompok), aturan_list in aturan_kelompok.items():
        # Ambil semua gejala yang dibutuhkan oleh rule ini
        gejala_di_rule = set(aturan.gejala.kodeGejala for aturan in aturan_list)
        
        # CEK APAKAH USER MEMILIH GEJALA SAMA PERSIS DENGAN YANG ADA DI RULE (Strict Equality Matching)
        if gejala_di_rule == working_memory:
            # Berhasil temukan exact match
            try:
                kondisi_saat_ini = Kondisi.objects.get(kodeKondisi=kode_kondisi)
                diagnosis_terbaik = kondisi_saat_ini
                break  # Hentikan pencarian karena sudah ditemukan exact match
                
            except Kondisi.DoesNotExist:
                # Jika kondisi tidak ditemukan, lanjutkan ke kelompok aturan berikutnya
                continue
    
    # Jika ditemukan diagnosis dengan exact match, gunakan itu
    if diagnosis_terbaik:
        konsultasi.hasilKondisi = diagnosis_terbaik
        diagnosis_ditemukan = True
    else:
        # Tidak ada satupun kelompok aturan yang cocok persis
        # Set konsultasi.hasilKondisi = None
        konsultasi.hasilKondisi = None
        # Sistem harus mengirimkan sinyal ke view/template bahwa 
        # "Gejala yang dipilih tidak sesuai dengan kombinasi rule diagnosis manapun"
    
    # Output dan Penyimpanan
    # Simpan (.save()) objek Konsultasi yang sudah diisi hasilKondisi
    konsultasi.save()
    
    # Kembalikan objek Konsultasi yang berisi hasil diagnosa
    return konsultasi


# FUNGSI mesin infrerensi
def dokumentasi_logika_rule(kode_gejala_input):
    """
    Fungsi ini hanya digunakan sebagai dokumentasi logika implementasi rule untuk Bab 4 Skripsi.
    Fungsi ini tidak digunakan dalam sistem produksi.
    """
    working_memory = set(kode_gejala_input)
    
    # Rule 1: K01 - Stunting
    if working_memory == {'G01', 'G09'}:
        return 'K01 (Stunting)'
    
    # Rule 2: K02 - Gizi Buruk
    elif working_memory == {'G02', 'G03', 'G07', 'G08', 'G09'} or \
         working_memory == {'G02', 'G03', 'G07', 'G08', 'G09', 'G14', 'G15'}:
        return 'K02 (Gizi Buruk)'
    
    # Rule 3: K03 - Risiko Stunting
    elif working_memory == {'G02', 'G03', 'G04', 'G06', 'G10', 'G12'} or \
         working_memory == {'G02', 'G03', 'G04', 'G06', 'G10', 'G11', 'G12', 'G15'}:
        return 'K03 (Risiko Stunting)'
    
    # Rule 4: K04 - Infeksi Berulang
    elif working_memory == {'G05', 'G09', 'G13'}:
        return 'K04 (Infeksi Berulang)'
    
    # Rule 5: K05 - Pola Makan/Gangguan Makan
    elif working_memory == {'G04', 'G06', 'G16', 'G17', 'G18', 'G19', 'G20'} or \
         working_memory == {'G04', 'G16', 'G17', 'G18', 'G19'}:
        return 'K05 (Pola Makan/Gangguan Makan)'
    
    # Rule 6: K06 - Kondisi Lainnya
    elif working_memory == {'G21', 'G22', 'G23', 'G24', 'G25'}:
        return 'K06'
    
    # Else: Hasil Tidak Diketahui
    else:
        return 'Hasil Tidak Diketahui - Tidak ada kombinasi rule yang sesuai'


# PROMPT #2: Views Django untuk Input dan Tampilan Hasil
def form_diagnosa(request):
    """
    View untuk menampilkan form diagnosa dan memproses input gejala
    """
    # Pastikan pengguna sudah login
    if 'pasien_id' not in request.session:
        return redirect('login_pasien')
    
    if request.method == 'GET':
        # Metode GET: Ambil dan tampilkan semua objek Gejala untuk ditampilkan dalam formulir HTML
        gejala_list = Gejala.objects.all()
        return render(request, 'diagnosa_form.html', {'gejala_list': gejala_list})
    
    elif request.method == 'POST':
        # Metode POST: Proses input dari form
        # Dapatkan daftar gejala yang dicentang dari checkbox
        kode_gejala_input = request.POST.getlist('gejala')
        
        # Ambil pasien_id dari sesi
        pasien_id = request.session.get('pasien_id')
        
        # Panggil fungsi jalankan_inferensi(pasien_id, kode_gejala_input)
        konsultasi = jalankan_inferensi(pasien_id, kode_gejala_input)
        
        # Redirect pengguna ke View tampilkan_hasil_diagnosa dengan ID Konsultasi yang baru dibuat
        return redirect('tampilkan_hasil_diagnosa', konsultasi_id=konsultasi.id)


def tampilkan_hasil_diagnosa(request, konsultasi_id):
    """
    View untuk menampilkan hasil diagnosa
    """
    # Pastikan pengguna sudah login
    if 'pasien_id' not in request.session:
        return redirect('login_pasien')
    
    try:
        # Ambil objek Konsultasi berdasarkan konsultasi_id
        konsultasi = Konsultasi.objects.select_related('hasilKondisi').get(id=konsultasi_id)
    except Konsultasi.DoesNotExist:
        # Jika konsultasi tidak ditemukan, redirect ke dashboard dengan pesan error
        return render(request, 'dashboard_pasien.html', {
            'error': 'Data konsultasi tidak ditemukan'
        })
    
    # Ambil objek Kondisi yang menjadi hasil diagnosa
    kondisi = konsultasi.hasilKondisi
    
    # For now, we'll assume it's not a partial diagnosis when displaying results
    # In a production system, we would store this information in the database
    diagnosis_parsial = False
    
    # Jika tidak ada hasil diagnosa
    if not kondisi:
        # Siapkan konteks untuk template dengan pesan bahwa tidak ada hasil
        context = {
            'konsultasi': konsultasi,
            'kondisi': None,
            'error': 'Gejala yang dipilih tidak sesuai dengan kombinasi rule diagnosis manapun',
            'diagnosis_parsial': diagnosis_parsial,
        }
    else:
        # Siapkan konteks untuk template
        context = {
            'konsultasi': konsultasi,
            'kondisi': kondisi,
            'diagnosis_parsial': diagnosis_parsial,
        }
    
    # Tampilkan namaKondisi, deskripsi, dan solusi dari hasil diagnosa tersebut
    return render(request, 'hasil_diagnosa.html', context)


# PROMPT #4: Keamanan dan Autentikasi Pasien
def registrasi_pasien(request):
    """
    View untuk menangani pendaftaran Pasien baru
    """
    if request.method == 'POST':
        # Terima data dari form
        nama_pengguna = request.POST.get('nama_pengguna')
        kata_sandi = request.POST.get('kata_sandi')
        nama = request.POST.get('nama')
        jenis_kelamin = request.POST.get('jenis_kelamin')
        tanggal_lahir = request.POST.get('tanggal_lahir')
        nama_wali = request.POST.get('nama_wali')
        nomor_telepon = request.POST.get('nomor_telepon')
        
        # Buat objek Pasien baru
        pasien = Pasien(
            namaPengguna=nama_pengguna,
            nama=nama,
            jenisKelamin=jenis_kelamin,
            tanggalLahir=tanggal_lahir,
            namaWali=nama_wali,
            nomorTelepon=nomor_telepon
        )
        
        # PENTING: Sebelum menyimpan, panggil metode set_password pada objek Pasien
        pasien.set_password(kata_sandi)
        
        # Simpan objek Pasien
        pasien.save()
        
        # Setelah registrasi sukses, redirect ke halaman login
        return redirect('login_pasien')
    
    # Metode GET: Tampilkan form registrasi
    return render(request, 'registrasi_pasien.html')


def login_pasien(request):
    """
    View untuk login Pasien
    """
    if request.method == 'POST':
        # Terima namaPengguna dan kataSandi mentah
        nama_pengguna = request.POST.get('nama_pengguna')
        kata_sandi = request.POST.get('kata_sandi')
        
        try:
            # Cari objek Pasien berdasarkan namaPengguna
            pasien = Pasien.objects.get(namaPengguna=nama_pengguna)
            
            # Gunakan metode check_password untuk memverifikasi kata sandi
            if pasien.check_password(kata_sandi):
                # Jika autentikasi sukses, buat sesi Django untuk Pasien tersebut
                request.session['pasien_id'] = pasien.id
                request.session['pasien_nama'] = pasien.nama
                
                # Redirect ke Dashboard Pasien
                return redirect('dashboard_pasien')
            else:
                # Jika password salah
                return render(request, 'login_pasien.html', {'error': 'Nama pengguna atau kata sandi salah'})
        except Pasien.DoesNotExist:
            # Jika pengguna tidak ditemukan
            return render(request, 'login_pasien.html', {'error': 'Nama pengguna atau kata sandi salah'})
    
    # Metode GET: Tampilkan form login
    return render(request, 'login_pasien.html')


def logout_pasien(request):
    """
    View untuk logout Pasien
    """
    # Hapus semua data Pasien dari sesi
    request.session.flush()
    
    # Redirect ke halaman login
    return redirect('home')


def logout_pakar(request):
    """
    View untuk logout Pakar
    """
    # Logout user
    from django.contrib.auth import logout
    logout(request)
    
    # Redirect ke halaman login pakar
    return redirect('login_pakar')


def dashboard_pasien(request):
    """
    View untuk dashboard Pasien
    """
    # Pastikan pengguna sudah login (cek pasien_id di sesi)
    if 'pasien_id' not in request.session:
        return redirect('login_pasien')
    
    # Ambil data Pasien yang sedang login
    pasien_id = request.session.get('pasien_id')
    try:
        pasien = Pasien.objects.get(id=pasien_id)
    except Pasien.DoesNotExist:
        # Jika pasien tidak ditemukan, hapus sesi dan arahkan ke login
        request.session.flush()
        return redirect('login_pasien')
    
    # Tampilkan ucapan selamat datang dan tautan ke fungsi diagnostik
    context = {
        'pasien': pasien
    }
    
    return render(request, 'dashboard_pasien.html', context)


def edit_akun_pasien(request):
    """
    View untuk mengelola dan memperbarui informasi pribadi Pasien
    """
    # Pastikan pengguna sudah login (cek pasien_id di sesi)
    if 'pasien_id' not in request.session:
        return redirect('login_pasien')
    
    # Ambil data Pasien yang sedang login
    pasien_id = request.session.get('pasien_id')
    try:
        pasien = Pasien.objects.get(id=pasien_id)
    except Pasien.DoesNotExist:
        # Jika pasien tidak ditemukan, hapus sesi dan arahkan ke login
        request.session.flush()
        return redirect('login_pasien')
    
    if request.method == 'GET':
        # Metode GET: Tampilkan formulir yang sudah terisi dengan data Pasien saat ini
        context = {
            'pasien': pasien
        }
        return render(request, 'edit_akun_pasien.html', context)
    
    elif request.method == 'POST':
        # Metode POST: Proses pembaruan data Pasien
        nama = request.POST.get('nama')
        nama_wali = request.POST.get('nama_wali')
        nomor_telepon = request.POST.get('nomor_telepon')
        kata_sandi_baru = request.POST.get('kata_sandi_baru')
        
        # Validasi data
        if not nama:
            context = {
                'pasien': pasien,
                'error': 'Nama tidak boleh kosong'
            }
            return render(request, 'edit_akun_pasien.html', context)
        
        # Update data pasien
        pasien.nama = nama
        pasien.namaWali = nama_wali or None
        pasien.nomorTelepon = nomor_telepon or None
        
        # Jika bidang kataSandi_baru diisi, perbarui kata sandi dengan aman
        if kata_sandi_baru:
            if len(kata_sandi_baru) < 6:
                context = {
                    'pasien': pasien,
                    'error': 'Kata sandi minimal 6 karakter'
                }
                return render(request, 'edit_akun_pasien.html', context)
            pasien.set_password(kata_sandi_baru)
        
        # Simpan perubahan
        pasien.save()
        
        # Berikan pesan sukses dan redirect ke dashboard
        return redirect('dashboard_pasien')


# PROMPT #5: Data Klinis (Input, Z-Score Akurat, & Grafik)
def input_pengukuran(request):
    """
    View untuk input data pengukuran fisik
    """
    # Pastikan pengguna sudah login
    if 'pasien_id' not in request.session:
        return redirect('login_pasien')
    
    # Ambil pasien yang sedang login
    pasien_id = request.session.get('pasien_id')
    try:
        pasien = Pasien.objects.get(id=pasien_id)
    except Pasien.DoesNotExist:
        request.session.flush()
        return redirect('login_pasien')
    
    if request.method == 'GET':
        # Metode GET: Tampilkan formulir untuk input tanggalUkur, beratBadan, dan tinggiBadan
        # Ambil riwayat pengukuran untuk ditampilkan
        pengukuran_list = PengukuranFisik.objects.filter(pasien=pasien).order_by('-tanggalUkur')[:5]  # 5 terakhir
        return render(request, 'input_pengukuran.html', {'pengukuran_list': pengukuran_list})
    
    elif request.method == 'POST':
        # Metode POST: Validasi input dan buat objek PengukuranFisik baru
        tanggal_ukur = request.POST.get('tanggal_ukur')
        berat_badan = request.POST.get('berat_badan')
        tinggi_badan = request.POST.get('tinggi_badan')
        lingkar_kepala = request.POST.get('lingkar_kepala')
        lingkar_lengan = request.POST.get('lingkar_lengan')
        imunisasi = request.POST.get('imunisasi')
        
        # Validasi input
        if not all([tanggal_ukur, berat_badan, tinggi_badan]):
            pengukuran_list = PengukuranFisik.objects.filter(pasien=pasien).order_by('-tanggalUkur')[:5]
            return render(request, 'input_pengukuran.html', {
                'error': 'Field wajib (tanggal ukur, berat badan, tinggi badan) harus diisi',
                'pengukuran_list': pengukuran_list
            })
        
        try:
            # Validasi format tanggal
            from datetime import datetime, date
            tanggal_ukur_date = datetime.strptime(tanggal_ukur, '%Y-%m-%d').date()
            
            # Validasi bahwa tanggal tidak di masa depan
            if tanggal_ukur_date > date.today():
                pengukuran_list = PengukuranFisik.objects.filter(pasien=pasien).order_by('-tanggalUkur')[:5]
                return render(request, 'input_pengukuran.html', {
                    'error': 'Tanggal pengukuran tidak boleh di masa depan',
                    'pengukuran_list': pengukuran_list
                })
            
            # Validasi bahwa tanggal tidak sebelum tanggal lahir pasien
            if tanggal_ukur_date < pasien.tanggalLahir:
                pengukuran_list = PengukuranFisik.objects.filter(pasien=pasien).order_by('-tanggalUkur')[:5]
                return render(request, 'input_pengukuran.html', {
                    'error': 'Tanggal pengukuran tidak boleh sebelum tanggal lahir pasien',
                    'pengukuran_list': pengukuran_list
                })
            
            # Buat objek PengukuranFisik baru, hubungkan dengan Pasien yang sedang login
            pengukuran_data = {
                'pasien': pasien,
                'tanggalUkur': tanggal_ukur,
                'beratBadan': berat_badan,
                'tinggiBadan': tinggi_badan,
            }
            
            # Tambahkan field opsional jika ada
            if lingkar_kepala:
                pengukuran_data['lingkarKepala'] = lingkar_kepala
            if lingkar_lengan:
                pengukuran_data['lingkarLengan'] = lingkar_lengan
            if imunisasi:
                pengukuran_data['imunisasi'] = imunisasi
            
            pengukuran = PengukuranFisik.objects.create(**pengukuran_data)
            
            # Segera panggil hitung_dan_simpan_zscore(pengukuran_id) pada objek baru tersebut
            try:
                hitung_dan_simpan_zscore(pengukuran.id)
            except ValueError as e:
                # Jika ada error dalam perhitungan Z-score, hapus pengukuran dan tampilkan error
                pengukuran.delete()
                pengukuran_list = PengukuranFisik.objects.filter(pasien=pasien).order_by('-tanggalUkur')[:5]
                return render(request, 'input_pengukuran.html', {
                    'error': f'Error dalam perhitungan Z-score: {str(e)}',
                    'pengukuran_list': pengukuran_list
                })
            
            # Panggil buat_jadwal_notifikasi(pengukuran) untuk membuat jadwal notifikasi pengukuran ulang
            try:
                buat_jadwal_notifikasi(pengukuran)
            except ValueError as e:
                print(f"Error membuat notifikasi: {str(e)}")
                # Lanjutkan meski gagal membuat notifikasi
            
            # Redirect ke dashboard atau halaman grafik
            return redirect('tampilkan_grafik_riwayat', pasien_id=pasien_id)
            
        except ValueError as e:
            pengukuran_list = PengukuranFisik.objects.filter(pasien=pasien).order_by('-tanggalUkur')[:5]
            return render(request, 'input_pengukuran.html', {
                'error': f'Format tanggal tidak valid: {str(e)}',
                'pengukuran_list': pengukuran_list
            })
        except Exception as e:
            pengukuran_list = PengukuranFisik.objects.filter(pasien=pasien).order_by('-tanggalUkur')[:5]
            return render(request, 'input_pengukuran.html', {
                'error': f'Terjadi kesalahan: {str(e)}',
                'pengukuran_list': pengukuran_list
            })

def daftar_notifikasi(request):
    pasien_id = request.session.get('pasien_id')
    if not pasien_id:
        return redirect('login_pasien')
    
    # Ambil semua notifikasi untuk pasien ini, urutkan dari yang terbaru
    notifikasi_list = Notifikasi.objects.filter(pasien_id=pasien_id).order_by('-jadwalNotifikasi')
    
    # Tandai semua notifikasi yang sudah jatuh tempo sebagai 'sudah terkirim' saat dibuka
    from django.utils import timezone
    notifikasi_list.filter(jadwalNotifikasi__lte=timezone.now()).update(sudahTerkirim=True)
    
    return render(request, 'notifikasi_list.html', {'notifikasi_list': notifikasi_list})
def tampilkan_grafik_riwayat(request, pasien_id):
    """
    View untuk menampilkan grafik riwayat pengukuran fisik
    
    Args:
        pasien_id: ID pasien
    """
    # Pastikan pengguna sudah login
    if 'pasien_id' not in request.session:
        return redirect('login_pasien')
        
    # Ambil semua data PengukuranFisik untuk pasien_id yang diurutkan berdasarkan tanggal
    pengukuran_list = PengukuranFisik.objects.filter(pasien_id=pasien_id).order_by('tanggalUkur')
    
    # Ubah data menjadi format JSON yang optimal untuk client-side rendering
    data_bb_u = []
    data_tb_u = []
    
    for pengukuran in pengukuran_list:
        data_bb_u.append({
            'tgl': pengukuran.tanggalUkur.strftime('%Y-%m-%d'),
            'score': float(pengukuran.skor_Z_BB_U) if pengukuran.skor_Z_BB_U is not None else None
        })
        
        data_tb_u.append({
            'tgl': pengukuran.tanggalUkur.strftime('%Y-%m-%d'),
            'score': float(pengukuran.skor_Z_TB_U) if pengukuran.skor_Z_TB_U is not None else None
        })
    
    # Kembalikan data untuk rendering grafik di template
    context = {
        'data_bb_u': data_bb_u,
        'data_tb_u': data_tb_u,
        'pasien_id': pasien_id,
    }
    
    return render(request, 'grafik_riwayat.html', context)


# Expert/Admin Views
@login_required
@user_passes_test(is_expert)
@transaction.atomic
def create_rule_group(request):
    """
    View untuk membuat satu Kelompok Aturan (Rule Group) baru
    """
    kondisi_list = Kondisi.objects.all()
    gejala_list = Gejala.objects.all()
    
    if request.method == 'POST':
        # Validasi input
        kondisi_id = request.POST.get('kondisi')
        gejala_ids = request.POST.getlist('gejala')
        kode_kelompok = request.POST.get('kode_kelompok')
        
        if not all([kondisi_id, gejala_ids, kode_kelompok]):
            return render(request, 'pakar_create_rule.html', {
                'kondisi_list': kondisi_list,
                'gejala_list': gejala_list,
                'error': 'Semua field harus diisi',
                'page_title': 'Tambah Aturan Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Aturan', 'list_rules_pakar'),
                    ('Tambah Aturan', 'create_rule_group'),
                ]
            })
        
        try:
            # Ambil Kondisi
            kondisi = Kondisi.objects.get(kodeKondisi=kondisi_id)
            
            # Untuk setiap Gejala yang dipilih, buat entri terpisah dalam tabel Aturan
            for gejala_id in gejala_ids:
                gejala = Gejala.objects.get(kodeGejala=gejala_id)
                Aturan.objects.create(
                    kondisi=kondisi,
                    gejala=gejala,
                    kodeKelompokAturan=kode_kelompok
                )
            
            # Redirect ke daftar aturan
            return redirect('list_rules_pakar')
            
        except Exception as e:
            return render(request, 'pakar_create_rule.html', {
                'kondisi_list': kondisi_list,
                'gejala_list': gejala_list,
                'error': f'Terjadi kesalahan: {str(e)}',
                'page_title': 'Tambah Aturan Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Aturan', 'list_rules_pakar'),
                    ('Tambah Aturan', 'create_rule_group'),
                ]
            })
    
    # Metode GET: Tampilkan formulir
    return render(request, 'pakar_create_rule.html', {
        'kondisi_list': kondisi_list,
        'gejala_list': gejala_list,
        'page_title': 'Tambah Aturan Baru',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Aturan', 'list_rules_pakar'),
            ('Tambah Aturan', 'create_rule_group'),
        ]
    })


@login_required
@user_passes_test(is_expert)
def list_patients_pakar(request):
    """
    View untuk menampilkan daftar semua Pasien
    """
    # Ambil semua pasien
    pasien_list = Pasien.objects.all().order_by('nama')
    
    context = {
        'pasien_list': pasien_list,
        'page_title': 'Daftar Pasien',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Pasien', 'list_patients_pakar'),
        ]
    }
    
    return render(request, 'pakar_list_patients.html', context)


@login_required
@user_passes_test(is_expert)
def detail_pasien_pakar(request, pasien_id):
    """
    View untuk menampilkan ringkasan data Pasien untuk Pakar
    """
    # Ambil data pasien
    try:
        pasien = Pasien.objects.get(id=pasien_id)
    except Pasien.DoesNotExist:
        # Jika pasien tidak ditemukan, tampilkan pesan error
        return render(request, 'pakar_list_patients.html', {
            'error': 'Pasien tidak ditemukan'
        })
    
    # Ambil semua data PengukuranFisik
    pengukuran_list = PengukuranFisik.objects.filter(pasien=pasien).order_by('-tanggalUkur')
    
    # Ambil riwayat Konsultasi
    konsultasi_list = Konsultasi.objects.filter(pasien=pasien).order_by('-tanggalKonsultasi')
    
    # Untuk setiap konsultasi, ambil detail gejala
    for konsultasi in konsultasi_list:
        konsultasi.detail_gejala = DetailKonsultasi.objects.filter(konsultasi=konsultasi).select_related('gejala')
    
    return render(request, 'pakar_detail_pasien.html', {
        'pasien': pasien,
        'pengukuran_list': pengukuran_list,
        'konsultasi_list': konsultasi_list
    })


@login_required
@user_passes_test(is_expert)
def list_rules_pakar(request):
    """
    View untuk menampilkan daftar semua Aturan yang terstruktur
    """
    # Ambil semua aturan dan kelompokkan berdasarkan kodeKelompokAturan
    aturan_list = Aturan.objects.select_related('kondisi', 'gejala').order_by('kodeKelompokAturan')
    
    # Kelompokkan aturan berdasarkan kodeKelompokAturan dan kondisi
    aturan_kelompok = defaultdict(list)
    for aturan in aturan_list:
        key = (aturan.kodeKelompokAturan, aturan.kondisi)
        aturan_kelompok[key].append(aturan)
    
    context = {
        'aturan_kelompok': dict(aturan_kelompok),
        'page_title': 'Daftar Aturan',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Aturan', 'list_rules_pakar'),
        ]
    }
    
    return render(request, 'pakar_list_rules.html', context)


@login_required
@user_passes_test(is_expert)
def show_rule_detail(request, pk):
    """
    View untuk menampilkan detail aturan diagnosa
    """
    # Ambil kondisi berdasarkan pk
    try:
        kondisi = Kondisi.objects.get(kodeKondisi=pk)
    except Kondisi.DoesNotExist:
        return render(request, 'pakar_list_rules.html', {
            'error': 'Aturan tidak ditemukan'
        })
    
    # Ambil semua aturan yang terkait dengan kondisi ini
    aturan_list = Aturan.objects.filter(kondisi=kondisi).select_related('gejala').order_by('kodeKelompokAturan')
    
    # Kelompokkan aturan berdasarkan kodeKelompokAturan
    aturan_kelompok = defaultdict(list)
    for aturan in aturan_list:
        aturan_kelompok[aturan.kodeKelompokAturan].append(aturan)
    
    context = {
        'kondisi': kondisi,
        'aturan_kelompok': dict(aturan_kelompok),
        'page_title': f'Detail Aturan: {kondisi.kodeKondisi} - {kondisi.namaKondisi}',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Aturan', 'list_rules_pakar'),
            (f'{kondisi.kodeKondisi} - {kondisi.namaKondisi}', None),
        ]
    }
    
    return render(request, 'pakar_rule_detail.html', context)


@login_required
@user_passes_test(is_expert)
@transaction.atomic
def edit_rule_pakar(request, pk):
    """
    View untuk mengedit semua aturan yang terkait dengan satu Kondisi
    """
    kondisi = get_object_or_404(Kondisi, pk=pk)
    aturan_list = Aturan.objects.filter(kondisi=kondisi)
    gejala_list = Gejala.objects.all()
    
    # Group aturan by kodeKelompokAturan for easier editing
    rule_groups = {}
    for aturan in aturan_list:
        if aturan.kodeKelompokAturan not in rule_groups:
            rule_groups[aturan.kodeKelompokAturan] = []
        rule_groups[aturan.kodeKelompokAturan].append(aturan)
    
    if request.method == 'POST':
        # Handle form submission for updating rules
        try:
            # Clear existing rules for this condition
            Aturan.objects.filter(kondisi=kondisi).delete()
            
            # Process submitted rule groups
            rule_group_indices = []
            for key in request.POST.keys():
                if key.startswith('rule_group_'):
                    try:
                        group_index = key.split('_')[2]
                        rule_group_indices.append(int(group_index))
                    except (IndexError, ValueError):
                        continue
            
            # Process each rule group
            for group_index in rule_group_indices:
                gejala_ids = request.POST.getlist(f'gejala_{group_index}')
                kode_kelompok = request.POST.get(f'kode_kelompok_{group_index}', f'R{int(group_index)+1:02d}')
                
                # Only create rules if at least one gejala is selected
                if gejala_ids:
                    # Create new rules for each selected gejala
                    for gejala_id in gejala_ids:
                        if gejala_id:  # Only if a gejala is selected
                            try:
                                gejala = Gejala.objects.get(kodeGejala=gejala_id)
                                Aturan.objects.create(
                                    kondisi=kondisi,
                                    gejala=gejala,
                                    kodeKelompokAturan=kode_kelompok
                                )
                            except Gejala.DoesNotExist:
                                # Skip invalid gejala IDs
                                continue
            
            messages.success(request, f'Aturan untuk Kondisi {kondisi.namaKondisi} berhasil diperbarui.')
            return redirect('list_rules_pakar')
            
        except Exception as e:
            messages.error(request, f'Terjadi kesalahan saat memperbarui aturan: {str(e)}')
            # Re-fetch aturan_list as they might have been deleted
            aturan_list = Aturan.objects.filter(kondisi=kondisi)
            rule_groups = {}
            for aturan in aturan_list:
                if aturan.kodeKelompokAturan not in rule_groups:
                    rule_groups[aturan.kodeKelompokAturan] = []
                rule_groups[aturan.kodeKelompokAturan].append(aturan)

    context = {
        'page_title': f"Edit Aturan: {kondisi.namaKondisi}",
        # Removed breadcrumb_items to avoid redundancy with page_title
        'kondisi': kondisi,
        'aturan_list': aturan_list,
        'rule_groups': rule_groups,
        'gejala_list': gejala_list,
    }
    return render(request, 'pakar_form_rule.html', context)


@login_required
@user_passes_test(is_expert)
def delete_rule_pakar(request, pk):
    """
    View untuk menghapus semua aturan yang terkait dengan satu Kondisi
    """
    # Mengambil Kondisi karena aturan dikelompokkan berdasarkan Kondisi (pk)
    kondisi = get_object_or_404(Kondisi, pk=pk)
    
    if request.method == 'POST':
        # Hapus semua aturan yang terkait dengan kondisi ini
        Aturan.objects.filter(kondisi=kondisi).delete()
        messages.success(request, f'Semua Aturan untuk Kondisi "{kondisi.namaKondisi}" berhasil dihapus.')
        return redirect('list_rules_pakar')

    context = {
        'page_title': f"Konfirmasi Hapus Aturan",
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Aturan', 'list_rules_pakar'),
            ('Hapus Aturan', None),
        ],
        'kondisi': kondisi,
        'aturan_count': Aturan.objects.filter(kondisi=kondisi).count(),
    }
    return render(request, 'pakar_confirm_delete.html', context) # Template konfirmasi


@login_required
@user_passes_test(is_expert)
def dashboard_pakar(request):
    """
    View untuk dashboard Pakar - menampilkan statistik sistem
    """
    # Ambil statistik sistem
    total_pasien = Pasien.objects.count()
    total_konsultasi = Konsultasi.objects.count()
    total_gejala = Gejala.objects.count()
    total_kondisi = Kondisi.objects.count()
    total_aturan = Aturan.objects.count()
    
    context = {
        'total_pasien': total_pasien,
        'total_konsultasi': total_konsultasi,
        'total_gejala': total_gejala,
        'total_kondisi': total_kondisi,
        'total_aturan': total_aturan,
        'page_title': 'Dashboard Pakar',
        # Removed breadcrumb_items to avoid redundancy with page_title
    }
    
    return render(request, 'dashboard_pakar.html', context)


@login_required
@user_passes_test(is_expert)
def pakar_help(request):
    """
    View untuk halaman bantuan penggunaan sistem bagi Pakar
    """
    context = {
        'page_title': 'Cara Penggunaan Sistem',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Help', 'pakar_help'),
        ]
    }
    
    return render(request, 'pakar_help.html', context)

# Custom login view for experts
def login_pakar(request):
    """
    View khusus untuk login Pakar Diagnosa
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user is staff and belongs to "Pakar Diagnosa" group
            if user.is_staff and user.groups.filter(name='Pakar Diagnosa').exists():
                login(request, user)
                # Redirect to pakar patients list
                return redirect('list_patients_pakar')
            else:
                # User is not authorized as expert
                return render(request, 'login_pakar.html', {
                    'error': 'Anda tidak memiliki izin untuk mengakses halaman ini.'
                })
        else:
            # Invalid credentials
            return render(request, 'login_pakar.html', {
                'error': 'Username atau password salah.'
            })
    
    # GET request - show login form
    return render(request, 'login_pakar.html')


@login_required
@user_passes_test(is_expert)
def list_gejala_pakar(request):
    """
    View untuk menampilkan daftar semua Gejala
    """
    gejala_list = Gejala.objects.all().order_by('kodeGejala')
    
    context = {
        'gejala_list': gejala_list,
        'page_title': 'Daftar Gejala',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Gejala', 'list_gejala_pakar'),
        ]
    }
    
    return render(request, 'pakar_list_gejala.html', context)


@login_required
@user_passes_test(is_expert)
def create_gejala_pakar(request):
    """
    View untuk membuat Gejala baru
    """
    if request.method == 'POST':
        kode_gejala = request.POST.get('kode_gejala')
        nama_gejala = request.POST.get('nama_gejala')
        bobot_gejala = request.POST.get('bobot_gejala')
        
        # Validasi data
        if not kode_gejala or not nama_gejala or not bobot_gejala:
            return render(request, 'pakar_form_gejala.html', {
                'error': 'Semua field harus diisi',
                'page_title': 'Tambah Gejala Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Gejala', 'list_gejala_pakar'),
                    ('Tambah Gejala', 'create_gejala_pakar'),
                ]
            })
        
        try:
            bobot_gejala = float(bobot_gejala)
            if bobot_gejala < 0.1 or bobot_gejala > 1.0:
                raise ValueError("Bobot harus antara 0.1 dan 1.0")
        except ValueError as e:
            return render(request, 'pakar_form_gejala.html', {
                'error': f'Bobot tidak valid: {str(e)}',
                'page_title': 'Tambah Gejala Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Gejala', 'list_gejala_pakar'),
                    ('Tambah Gejala', 'create_gejala_pakar'),
                ]
            })
        
        # Cek apakah kode gejala sudah ada
        if Gejala.objects.filter(kodeGejala=kode_gejala).exists():
            return render(request, 'pakar_form_gejala.html', {
                'error': 'Kode gejala sudah ada',
                'page_title': 'Tambah Gejala Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Gejala', 'list_gejala_pakar'),
                    ('Tambah Gejala', 'create_gejala_pakar'),
                ]
            })
        
        # Simpan gejala baru
        Gejala.objects.create(
            kodeGejala=kode_gejala,
            namaGejala=nama_gejala,
            bobotGejala=bobot_gejala
        )
        
        return redirect('list_gejala_pakar')
    
    context = {
        'page_title': 'Tambah Gejala Baru',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Gejala', 'list_gejala_pakar'),
            ('Tambah Gejala', 'create_gejala_pakar'),
        ]
    }
    
    return render(request, 'pakar_form_gejala.html', context)


@login_required
@user_passes_test(is_expert)
def edit_gejala_pakar(request, pk):
    """
    View untuk mengedit Gejala
    """
    try:
        gejala = Gejala.objects.get(kodeGejala=pk)
    except Gejala.DoesNotExist:
        return render(request, 'pakar_list_gejala.html', {
            'error': 'Gejala tidak ditemukan'
        })
    
    if request.method == 'POST':
        kode_gejala = request.POST.get('kode_gejala')
        nama_gejala = request.POST.get('nama_gejala')
        bobot_gejala = request.POST.get('bobot_gejala')
        
        # Validasi data
        if not kode_gejala or not nama_gejala or not bobot_gejala:
            return render(request, 'pakar_form_gejala.html', {
                'gejala': gejala,
                'error': 'Semua field harus diisi',
                'page_title': f'Edit Gejala: {gejala.kodeGejala}',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Gejala', 'list_gejala_pakar'),
                    (f'Edit {gejala.kodeGejala}', ''),
                ]
            })
        
        try:
            bobot_gejala = float(bobot_gejala)
            if bobot_gejala < 0.1 or bobot_gejala > 1.0:
                raise ValueError("Bobot harus antara 0.1 dan 1.0")
        except ValueError as e:
            return render(request, 'pakar_form_gejala.html', {
                'gejala': gejala,
                'error': f'Bobot tidak valid: {str(e)}',
                'page_title': f'Edit Gejala: {gejala.kodeGejala}',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Gejala', 'list_gejala_pakar'),
                    (f'Edit {gejala.kodeGejala}', ''),
                ]
            })
        
        # Cek apakah kode gejala sudah ada (selain untuk gejala ini sendiri)
        if Gejala.objects.filter(kodeGejala=kode_gejala).exclude(kodeGejala=pk).exists():
            return render(request, 'pakar_form_gejala.html', {
                'gejala': gejala,
                'error': 'Kode gejala sudah ada',
                'page_title': f'Edit Gejala: {gejala.kodeGejala}',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Gejala', 'list_gejala_pakar'),
                    (f'Edit {gejala.kodeGejala}', ''),
                ]
            })
        
        # Update gejala
        gejala.kodeGejala = kode_gejala
        gejala.namaGejala = nama_gejala
        gejala.bobotGejala = bobot_gejala
        gejala.save()
        
        return redirect('list_gejala_pakar')
    
    context = {
        'gejala': gejala,
        'page_title': f'Edit Gejala: {gejala.kodeGejala}',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Gejala', 'list_gejala_pakar'),
            (f'Edit {gejala.kodeGejala}', ''),
        ]
    }
    
    return render(request, 'pakar_form_gejala.html', context)


@login_required
@user_passes_test(is_expert)
def delete_gejala_pakar(request, pk):
    """
    View untuk menghapus Gejala
    """
    try:
        gejala = Gejala.objects.get(kodeGejala=pk)
        gejala.delete()
    except Gejala.DoesNotExist:
        pass  # Jika tidak ditemukan, abaikan
    
    return redirect('list_gejala_pakar')


@login_required
@user_passes_test(is_expert)
def list_kondisi_pakar(request):
    """
    View untuk menampilkan daftar semua Kondisi
    """
    kondisi_list = Kondisi.objects.all().order_by('kodeKondisi')
    
    context = {
        'kondisi_list': kondisi_list,
        'page_title': 'Daftar Kondisi',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Kondisi', 'list_kondisi_pakar'),
        ]
    }
    
    return render(request, 'pakar_list_kondisi.html', context)


@login_required
@user_passes_test(is_expert)
def create_kondisi_pakar(request):
    """
    View untuk membuat Kondisi baru
    """
    if request.method == 'POST':
        kode_kondisi = request.POST.get('kode_kondisi')
        nama_kondisi = request.POST.get('nama_kondisi')
        deskripsi = request.POST.get('deskripsi')
        solusi = request.POST.get('solusi')
        
        # Validasi data
        if not kode_kondisi or not nama_kondisi or not deskripsi or not solusi:
            return render(request, 'pakar_form_kondisi.html', {
                'error': 'Semua field harus diisi',
                'page_title': 'Tambah Kondisi Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Kondisi', 'list_kondisi_pakar'),
                    ('Tambah Kondisi', 'create_kondisi_pakar'),
                ]
            })
        
        # Cek apakah kode kondisi sudah ada
        if Kondisi.objects.filter(kodeKondisi=kode_kondisi).exists():
            return render(request, 'pakar_form_kondisi.html', {
                'error': 'Kode kondisi sudah ada',
                'page_title': 'Tambah Kondisi Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Kondisi', 'list_kondisi_pakar'),
                    ('Tambah Kondisi', 'create_kondisi_pakar'),
                ]
            })
        
        # Simpan kondisi baru
        Kondisi.objects.create(
            kodeKondisi=kode_kondisi,
            namaKondisi=nama_kondisi,
            deskripsi=deskripsi,
            solusi=solusi
        )
        
        return redirect('list_kondisi_pakar')
    
    context = {
        'page_title': 'Tambah Kondisi Baru',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Kondisi', 'list_kondisi_pakar'),
            ('Tambah Kondisi', 'create_kondisi_pakar'),
        ]
    }
    
    return render(request, 'pakar_form_kondisi.html', context)


@login_required
@user_passes_test(is_expert)
def edit_kondisi_pakar(request, pk):
    """
    View untuk mengedit Kondisi
    """
    try:
        kondisi = Kondisi.objects.get(kodeKondisi=pk)
    except Kondisi.DoesNotExist:
        return render(request, 'pakar_list_kondisi.html', {
            'error': 'Kondisi tidak ditemukan'
        })
    
    if request.method == 'POST':
        kode_kondisi = request.POST.get('kode_kondisi')
        nama_kondisi = request.POST.get('nama_kondisi')
        deskripsi = request.POST.get('deskripsi')
        solusi = request.POST.get('solusi')
        
        # Validasi data
        if not kode_kondisi or not nama_kondisi or not deskripsi or not solusi:
            return render(request, 'pakar_form_kondisi.html', {
                'kondisi': kondisi,
                'error': 'Semua field harus diisi',
                'page_title': f'Edit Kondisi: {kondisi.kodeKondisi}',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Kondisi', 'list_kondisi_pakar'),
                    (f'Edit {kondisi.kodeKondisi}', ''),
                ]
            })
        
        # Cek apakah kode kondisi sudah ada (selain untuk kondisi ini sendiri)
        if Kondisi.objects.filter(kodeKondisi=kode_kondisi).exclude(kodeKondisi=pk).exists():
            return render(request, 'pakar_form_kondisi.html', {
                'kondisi': kondisi,
                'error': 'Kode kondisi sudah ada',
                'page_title': f'Edit Kondisi: {kondisi.kodeKondisi}',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Kondisi', 'list_kondisi_pakar'),
                    (f'Edit {kondisi.kodeKondisi}', ''),
                ]
            })
        
        # Update kondisi
        kondisi.kodeKondisi = kode_kondisi
        kondisi.namaKondisi = nama_kondisi
        kondisi.deskripsi = deskripsi
        kondisi.solusi = solusi
        kondisi.save()
        
        return redirect('list_kondisi_pakar')
    
    context = {
        'kondisi': kondisi,
        'page_title': f'Edit Kondisi: {kondisi.kodeKondisi}',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Kondisi', 'list_kondisi_pakar'),
            (f'Edit {kondisi.kodeKondisi}', ''),
        ]
    }
    
    return render(request, 'pakar_form_kondisi.html', context)


@login_required
@user_passes_test(is_expert)
def delete_kondisi_pakar(request, pk):
    """
    View untuk menghapus Kondisi
    """
    try:
        kondisi = Kondisi.objects.get(kodeKondisi=pk)
        kondisi.delete()
    except Kondisi.DoesNotExist:
        pass  # Jika tidak ditemukan, abaikan
    
    return redirect('list_kondisi_pakar')


@login_required
@user_passes_test(is_expert)
def create_pasien_pakar(request):
    """
    View untuk membuat Pasien baru
    """
    if request.method == 'POST':
        # Terima data dari form
        nama_pengguna = request.POST.get('nama_pengguna')
        kata_sandi = request.POST.get('kata_sandi')
        nama = request.POST.get('nama')
        jenis_kelamin = request.POST.get('jenis_kelamin')
        tanggal_lahir = request.POST.get('tanggal_lahir')
        nama_wali = request.POST.get('nama_wali')
        nomor_telepon = request.POST.get('nomor_telepon')
        
        # Validasi data
        if not all([nama_pengguna, kata_sandi, nama, jenis_kelamin, tanggal_lahir]):
            return render(request, 'pakar_form_pasien.html', {
                'error': 'Field wajib harus diisi',
                'page_title': 'Tambah Pasien Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pasien', 'list_patients_pakar'),
                    ('Tambah Pasien', 'create_pasien_pakar'),
                ]
            })
        
        # Cek apakah nama pengguna sudah ada
        if Pasien.objects.filter(namaPengguna=nama_pengguna).exists():
            return render(request, 'pakar_form_pasien.html', {
                'error': 'Nama pengguna sudah digunakan',
                'page_title': 'Tambah Pasien Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pasien', 'list_patients_pakar'),
                    ('Tambah Pasien', 'create_pasien_pakar'),
                ]
            })
        
        try:
            # Buat objek Pasien baru
            pasien = Pasien(
                namaPengguna=nama_pengguna,
                nama=nama,
                jenisKelamin=jenis_kelamin,
                tanggalLahir=tanggal_lahir,
                namaWali=nama_wali or None,
                nomorTelepon=nomor_telepon or None
            )
            
            # PENTING: Sebelum menyimpan, panggil metode set_password pada objek Pasien
            pasien.set_password(kata_sandi)
            
            # Simpan objek Pasien
            pasien.save()
            
            # Redirect ke daftar pasien
            return redirect('list_patients_pakar')
            
        except Exception as e:
            return render(request, 'pakar_form_pasien.html', {
                'error': f'Terjadi kesalahan: {str(e)}',
                'page_title': 'Tambah Pasien Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pasien', 'list_patients_pakar'),
                    ('Tambah Pasien', 'create_pasien_pakar'),
                ]
            })
    
    # Metode GET: Tampilkan form
    context = {
        'page_title': 'Tambah Pasien Baru',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Pasien', 'list_patients_pakar'),
            ('Tambah Pasien', 'create_pasien_pakar'),
        ]
    }
    
    return render(request, 'pakar_form_pasien.html', context)


@login_required
@user_passes_test(is_expert)
def edit_pasien_pakar(request, pasien_id):
    """
    View untuk mengedit Pasien
    """
    try:
        pasien = Pasien.objects.get(id=pasien_id)
    except Pasien.DoesNotExist:
        return render(request, 'pakar_list_patients.html', {
            'error': 'Pasien tidak ditemukan'
        })
    
    if request.method == 'POST':
        # Terima data dari form
        nama = request.POST.get('nama')
        jenis_kelamin = request.POST.get('jenis_kelamin')
        tanggal_lahir = request.POST.get('tanggal_lahir')
        nama_wali = request.POST.get('nama_wali')
        nomor_telepon = request.POST.get('nomor_telepon')
        kata_sandi_baru = request.POST.get('kata_sandi_baru')
        
        # Validasi data
        if not all([nama, jenis_kelamin, tanggal_lahir]):
            return render(request, 'pakar_form_pasien.html', {
                'pasien': pasien,
                'error': 'Field wajib harus diisi',
                'page_title': f'Edit Pasien: {pasien.nama}',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pasien', 'list_patients_pakar'),
                    (f'Edit {pasien.nama}', ''),
                ]
            })
        
        try:
            # Update data pasien
            pasien.nama = nama
            pasien.jenisKelamin = jenis_kelamin
            pasien.tanggalLahir = tanggal_lahir
            pasien.namaWali = nama_wali or None
            pasien.nomorTelepon = nomor_telepon or None
            
            # Jika ada kata sandi baru, update
            if kata_sandi_baru:
                if len(kata_sandi_baru) < 6:
                    return render(request, 'pakar_form_pasien.html', {
                        'pasien': pasien,
                        'error': 'Kata sandi minimal 6 karakter',
                        'page_title': f'Edit Pasien: {pasien.nama}',
                        'breadcrumb_items': [
                            ('Dashboard', 'dashboard_pakar'),
                            ('Pasien', 'list_patients_pakar'),
                            (f'Edit {pasien.nama}', ''),
                        ]
                    })
                pasien.set_password(kata_sandi_baru)
            
            # Simpan perubahan
            pasien.save()
            
            # Redirect ke daftar pasien
            return redirect('list_patients_pakar')
            
        except Exception as e:
            return render(request, 'pakar_form_pasien.html', {
                'pasien': pasien,
                'error': f'Terjadi kesalahan: {str(e)}',
                'page_title': f'Edit Pasien: {pasien.nama}',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pasien', 'list_patients_pakar'),
                    (f'Edit {pasien.nama}', ''),
                ]
            })
    
    # Metode GET: Tampilkan form dengan data pasien
    context = {
        'pasien': pasien,
        'page_title': f'Edit Pasien: {pasien.nama}',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Pasien', 'list_patients_pakar'),
            (f'Edit {pasien.nama}', None),
        ]
    }
    
    return render(request, 'pakar_form_pasien.html', context)


@login_required
@user_passes_test(is_expert)
def delete_pasien_pakar(request, pasien_id):
    """
    View untuk menghapus Pasien
    """
    try:
        pasien = Pasien.objects.get(id=pasien_id)
        nama_pasien = pasien.nama
        
        if request.method == 'POST':
            # Hapus pasien
            pasien.delete()
            messages.success(request, f'Pasien "{nama_pasien}" berhasil dihapus.')
            return redirect('list_patients_pakar')
        
        # Metode GET: Tampilkan konfirmasi
        context = {
            'pasien': pasien,
            'page_title': f"Hapus Pasien: {nama_pasien}",
            'breadcrumb_items': [
                ('Dashboard', 'dashboard_pakar'),
                ('Pasien', 'list_patients_pakar'),
                (f'Hapus {nama_pasien}', None),
            ]
        }
        return render(request, 'pakar_confirm_delete_pasien.html', context)
        
    except Pasien.DoesNotExist:
        messages.error(request, 'Pasien tidak ditemukan.')
        return redirect('list_patients_pakar')


def riwayat_pengukuran(request):
    pasien_id = request.session.get('pasien_id')
    if not pasien_id:
        return redirect('login_pasien')
    pengukuran_list = PengukuranFisik.objects.filter(pasien_id=pasien_id).order_by('-tanggalUkur')
    return render(request, 'riwayat_list.html', {'pengukuran_list': pengukuran_list})


def cetak_riwayat_pdf(request):
    from io import BytesIO
    from xhtml2pdf import pisa
    from django.template.loader import get_template

    pasien_id = request.session.get('pasien_id')
    pasien = Pasien.objects.get(id=pasien_id)
    pengukuran_list = PengukuranFisik.objects.filter(pasien=pasien).order_by('-tanggalUkur')
    context = {'pasien': pasien, 'pengukuran_list': pengukuran_list}
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="riwayat_{pasien.nama}.pdf"'

    template = get_template('pdf/riwayat_pengukuran_pdf.html')
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)
    return response
def cetak_hasil_diagnosa_pdf(request, konsultasi_id):
    """
    View untuk mencetak hasil diagnosa dalam format PDF
    """
    from io import BytesIO
    from xhtml2pdf import pisa
    from django.template.loader import get_template
    
    # Pastikan pengguna sudah login
    if 'pasien_id' not in request.session:
        return redirect('login_pasien')
    
    # Ambil konsultasi berdasarkan konsultasi_id
    try:
        konsultasi = get_object_or_404(Konsultasi.objects.select_related('hasilKondisi'), id=konsultasi_id)
    except Konsultasi.DoesNotExist:
        return HttpResponse('Konsultasi tidak ditemukan', status=404)
    
    # Render template HTML untuk PDF
    template_path = 'pdf/hasil_diagnosa_pdf.html'
    context = {
        'konsultasi': konsultasi,
        'pasien': konsultasi.pasien,
        'kondisi': konsultasi.hasilKondisi
    }
    
    # Buat respons PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="diagnosa_{konsultasi.pasien.nama}.pdf"'
    
    # Render HTML ke PDF
    template = get_template(template_path)
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    return response


def riwayat_list(request):
    """
    View untuk menampilkan daftar riwayat pengukuran
    """
    # Pastikan pengguna adalah pasien
    if 'pasien_id' not in request.session:
        return redirect('login_pasien')
    
    # Dapatkan pasien_id dari session
    pasien_id = request.session['pasien_id']
    
    # Dapatkan daftar pengukuran untuk pasien tersebut, urutkan dari yang terbaru
    pengukuran_list = PengukuranFisik.objects.filter(pasien_id=pasien_id).order_by('-tanggalUkur')
    
    return render(request, 'riwayat_list.html', {
        'pengukuran_list': pengukuran_list
    })


def preview_diagnosa(request):
    """
    View untuk menampilkan preview hasil diagnosa sebelum dicetak
    """
    # Pastikan pengguna sudah login
    if 'pasien_id' not in request.session:
        return redirect('login_pasien')
    
    pasien_id = request.session.get('pasien_id')
    
    # Ambil konsultasi terakhir yang sudah ada hasil diagnosanya
    try:
        konsultasi = Konsultasi.objects.select_related('pasien', 'hasilKondisi').prefetch_related('detailkonsultasi_set__gejala').filter(pasien_id=pasien_id).latest('tanggalKonsultasi')
    except Konsultasi.DoesNotExist:
        return HttpResponse('Konsultasi tidak ditemukan', status=404)
    
    # Render template HTML untuk preview
    context = {
        'konsultasi': konsultasi,
        'pasien': konsultasi.pasien
    }
    
    return render(request, 'preview_diagnosa.html', context)


@login_required
@user_passes_test(is_expert)
def list_pengukuran_pakar(request):
    """
    View untuk menampilkan daftar semua Pengukuran
    """
    # Ambil semua pengukuran dengan informasi pasien
    pengukuran_list = PengukuranFisik.objects.select_related('pasien').order_by('-tanggalUkur')
    
    context = {
        'pengukuran_list': pengukuran_list,
        'page_title': 'Daftar Pengukuran',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Pengukuran', 'list_pengukuran_pakar'),
        ]
    }
    
    return render(request, 'pakar_list_pengukuran.html', context)


@login_required
@user_passes_test(is_expert)
def create_pengukuran_pakar(request):
    """
    View untuk membuat Pengukuran baru
    """
    # Ambil daftar pasien untuk dropdown
    pasien_list = Pasien.objects.all().order_by('nama')
    
    if request.method == 'POST':
        # Terima data dari form
        pasien_id = request.POST.get('pasien')
        tanggal_ukur = request.POST.get('tanggal_ukur')
        berat_badan = request.POST.get('berat_badan')
        tinggi_badan = request.POST.get('tinggi_badan')
        lingkar_kepala = request.POST.get('lingkar_kepala')
        lingkar_lengan = request.POST.get('lingkar_lengan')
        imunisasi = request.POST.get('imunisasi')
        
        # Validasi data
        if not all([pasien_id, tanggal_ukur, berat_badan, tinggi_badan]):
            return render(request, 'pakar_form_pengukuran.html', {
                'pasien_list': pasien_list,
                'error': 'Field wajib (pasien, tanggal ukur, berat badan, tinggi badan) harus diisi',
                'page_title': 'Tambah Pengukuran Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pengukuran', 'list_pengukuran_pakar'),
                    ('Tambah Pengukuran', 'create_pengukuran_pakar'),
                ]
            })
        
        try:
            # Ambil objek Pasien
            pasien = Pasien.objects.get(id=pasien_id)
            
            # Validasi format tanggal
            from datetime import datetime, date
            tanggal_ukur_date = datetime.strptime(tanggal_ukur, '%Y-%m-%d').date()
            
            # Validasi bahwa tanggal tidak di masa depan
            if tanggal_ukur_date > date.today():
                return render(request, 'pakar_form_pengukuran.html', {
                    'pasien_list': pasien_list,
                    'error': 'Tanggal pengukuran tidak boleh di masa depan',
                    'page_title': 'Tambah Pengukuran Baru',
                    'breadcrumb_items': [
                        ('Dashboard', 'dashboard_pakar'),
                        ('Pengukuran', 'list_pengukuran_pakar'),
                        ('Tambah Pengukuran', 'create_pengukuran_pakar'),
                    ]
                })
            
            # Validasi bahwa tanggal tidak sebelum tanggal lahir pasien
            if tanggal_ukur_date < pasien.tanggalLahir:
                return render(request, 'pakar_form_pengukuran.html', {
                    'pasien_list': pasien_list,
                    'error': 'Tanggal pengukuran tidak boleh sebelum tanggal lahir pasien',
                    'page_title': 'Tambah Pengukuran Baru',
                    'breadcrumb_items': [
                        ('Dashboard', 'dashboard_pakar'),
                        ('Pengukuran', 'list_pengukuran_pakar'),
                        ('Tambah Pengukuran', 'create_pengukuran_pakar'),
                    ]
                })
            
            # Buat objek PengukuranFisik baru
            pengukuran_data = {
                'pasien': pasien,
                'tanggalUkur': tanggal_ukur,
                'beratBadan': berat_badan,
                'tinggiBadan': tinggi_badan,
            }
            
            # Tambahkan field opsional jika ada
            if lingkar_kepala:
                pengukuran_data['lingkarKepala'] = lingkar_kepala
            if lingkar_lengan:
                pengukuran_data['lingkarLengan'] = lingkar_lengan
            if imunisasi:
                pengukuran_data['imunisasi'] = imunisasi
            
            pengukuran = PengukuranFisik.objects.create(**pengukuran_data)
            
            # Segera panggil hitung_dan_simpan_zscore(pengukuran_id) pada objek baru tersebut
            try:
                hitung_dan_simpan_zscore(pengukuran.id)
            except ValueError as e:
                # Jika ada error dalam perhitungan Z-score, hapus pengukuran dan tampilkan error
                pengukuran.delete()
                return render(request, 'pakar_form_pengukuran.html', {
                    'pasien_list': pasien_list,
                    'error': f'Error dalam perhitungan Z-score: {str(e)}',
                    'page_title': 'Tambah Pengukuran Baru',
                    'breadcrumb_items': [
                        ('Dashboard', 'dashboard_pakar'),
                        ('Pengukuran', 'list_pengukuran_pakar'),
                        ('Tambah Pengukuran', 'create_pengukuran_pakar'),
                    ]
                })
            
            # Redirect ke daftar pengukuran
            return redirect('list_pengukuran_pakar')
            
        except Pasien.DoesNotExist:
            return render(request, 'pakar_form_pengukuran.html', {
                'pasien_list': pasien_list,
                'error': 'Pasien tidak ditemukan',
                'page_title': 'Tambah Pengukuran Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pengukuran', 'list_pengukuran_pakar'),
                    ('Tambah Pengukuran', 'create_pengukuran_pakar'),
                ]
            })
        except ValueError as e:
            return render(request, 'pakar_form_pengukuran.html', {
                'pasien_list': pasien_list,
                'error': f'Format tanggal tidak valid: {str(e)}',
                'page_title': 'Tambah Pengukuran Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pengukuran', 'list_pengukuran_pakar'),
                    ('Tambah Pengukuran', 'create_pengukuran_pakar'),
                ]
            })
        except Exception as e:
            return render(request, 'pakar_form_pengukuran.html', {
                'pasien_list': pasien_list,
                'error': f'Terjadi kesalahan: {str(e)}',
                'page_title': 'Tambah Pengukuran Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pengukuran', 'list_pengukuran_pakar'),
                    ('Tambah Pengukuran', 'create_pengukuran_pakar'),
                ]
            })
    
    # Metode GET: Tampilkan form
    context = {
        'pasien_list': pasien_list,
        'page_title': 'Tambah Pengukuran Baru',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Pengukuran', 'list_pengukuran_pakar'),
            ('Tambah Pengukuran', 'create_pengukuran_pakar'),
        ]
    }
    
    return render(request, 'pakar_form_pengukuran.html', context)


@login_required
@user_passes_test(is_expert)
def edit_pengukuran_pakar(request, pk):
    """
    View untuk mengedit Pengukuran
    """
    try:
        pengukuran = PengukuranFisik.objects.select_related('pasien').get(id=pk)
    except PengukuranFisik.DoesNotExist:
        messages.error(request, 'Pengukuran tidak ditemukan.')
        return redirect('list_pengukuran_pakar')
    
    # Ambil daftar pasien untuk dropdown
    pasien_list = Pasien.objects.all().order_by('nama')
    
    if request.method == 'POST':
        # Terima data dari form
        pasien_id = request.POST.get('pasien')
        tanggal_ukur = request.POST.get('tanggal_ukur')
        berat_badan = request.POST.get('berat_badan')
        tinggi_badan = request.POST.get('tinggi_badan')
        lingkar_kepala = request.POST.get('lingkar_kepala')
        lingkar_lengan = request.POST.get('lingkar_lengan')
        imunisasi = request.POST.get('imunisasi')
        
        # Validasi data
        if not all([pasien_id, tanggal_ukur, berat_badan, tinggi_badan]):
            return render(request, 'pakar_form_pengukuran.html', {
                'pengukuran': pengukuran,
                'pasien_list': pasien_list,
                'error': 'Field wajib (pasien, tanggal ukur, berat badan, tinggi badan) harus diisi',
                'page_title': f'Edit Pengukuran: {pengukuran.tanggalUkur}',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pengukuran', 'list_pengukuran_pakar'),
                    (f'Edit {pengukuran.tanggalUkur}', None),
                ]
            })
        
        try:
            # Ambil objek Pasien
            pasien = Pasien.objects.get(id=pasien_id)
            
            # Validasi format tanggal
            from datetime import datetime, date
            tanggal_ukur_date = datetime.strptime(tanggal_ukur, '%Y-%m-%d').date()
            
            # Validasi bahwa tanggal tidak di masa depan
            if tanggal_ukur_date > date.today():
                return render(request, 'pakar_form_pengukuran.html', {
                    'pengukuran': pengukuran,
                    'pasien_list': pasien_list,
                    'error': 'Tanggal pengukuran tidak boleh di masa depan',
                    'page_title': f'Edit Pengukuran: {pengukuran.tanggalUkur}',
                    'breadcrumb_items': [
                        ('Dashboard', 'dashboard_pakar'),
                        ('Pengukuran', 'list_pengukuran_pakar'),
                        (f'Edit {pengukuran.tanggalUkur}', None),
                    ]
                })
            
            # Validasi bahwa tanggal tidak sebelum tanggal lahir pasien
            if tanggal_ukur_date < pasien.tanggalLahir:
                return render(request, 'pakar_form_pengukuran.html', {
                    'pengukuran': pengukuran,
                    'pasien_list': pasien_list,
                    'error': 'Tanggal pengukuran tidak boleh sebelum tanggal lahir pasien',
                    'page_title': f'Edit Pengukuran: {pengukuran.tanggalUkur}',
                    'breadcrumb_items': [
                        ('Dashboard', 'dashboard_pakar'),
                        ('Pengukuran', 'list_pengukuran_pakar'),
                        (f'Edit {pengukuran.tanggalUkur}', None),
                    ]
                })
            
            # Update data pengukuran
            pengukuran.pasien = pasien
            pengukuran.tanggalUkur = tanggal_ukur
            pengukuran.beratBadan = berat_badan
            pengukuran.tinggiBadan = tinggi_badan
            pengukuran.lingkarKepala = lingkar_kepala or None
            pengukuran.lingkarLengan = lingkar_lengan or None
            pengukuran.imunisasi = imunisasi or None
            
            # Simpan perubahan
            pengukuran.save()
            
            # Hitung ulang Z-score
            try:
                hitung_dan_simpan_zscore(pengukuran.id)
            except ValueError as e:
                messages.warning(request, f'Peringatan dalam perhitungan Z-score: {str(e)}')
            
            # Redirect ke daftar pengukuran
            return redirect('list_pengukuran_pakar')
            
        except Pasien.DoesNotExist:
            return render(request, 'pakar_form_pengukuran.html', {
                'pengukuran': pengukuran,
                'pasien_list': pasien_list,
                'error': 'Pasien tidak ditemukan',
                'page_title': f'Edit Pengukuran: {pengukuran.tanggalUkur}',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pengukuran', 'list_pengukuran_pakar'),
                    (f'Edit {pengukuran.tanggalUkur}', None),
                ]
            })
        except ValueError as e:
            return render(request, 'pakar_form_pengukuran.html', {
                'pengukuran': pengukuran,
                'pasien_list': pasien_list,
                'error': f'Format tanggal tidak valid: {str(e)}',
                'page_title': f'Edit Pengukuran: {pengukuran.tanggalUkur}',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pengukuran', 'list_pengukuran_pakar'),
                    (f'Edit {pengukuran.tanggalUkur}', None),
                ]
            })
        except Exception as e:
            return render(request, 'pakar_form_pengukuran.html', {
                'pengukuran': pengukuran,
                'pasien_list': pasien_list,
                'error': f'Terjadi kesalahan: {str(e)}',
                'page_title': f'Edit Pengukuran: {pengukuran.tanggalUkur}',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pengukuran', 'list_pengukuran_pakar'),
                    (f'Edit {pengukuran.tanggalUkur}', None),
                ]
            })
    
    # Metode GET: Tampilkan form dengan data pengukuran
    context = {
        'pengukuran': pengukuran,
        'pasien_list': pasien_list,
        'page_title': f'Edit Pengukuran: {pengukuran.tanggalUkur}',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Pengukuran', 'list_pengukuran_pakar'),
            (f'Edit {pengukuran.tanggalUkur}', None),
        ]
    }
    
    return render(request, 'pakar_form_pengukuran.html', context)


@login_required
@user_passes_test(is_expert)
def delete_pengukuran_pakar(request, pk):
    """
    View untuk menghapus Pengukuran
    """
    try:
        pengukuran = PengukuranFisik.objects.select_related('pasien').get(id=pk)
        tanggal_ukur = pengukuran.tanggalUkur
        nama_pasien = pengukuran.pasien.nama
        
        if request.method == 'POST':
            # Hapus pengukuran
            pengukuran.delete()
            messages.success(request, f'Pengukuran tanggal "{tanggal_ukur}" untuk pasien "{nama_pasien}" berhasil dihapus.')
            return redirect('list_pengukuran_pakar')
        
        # Metode GET: Tampilkan konfirmasi
        context = {
            'pengukuran': pengukuran,
            'page_title': f"Hapus Pengukuran: {tanggal_ukur}",
            'breadcrumb_items': [
                ('Dashboard', 'dashboard_pakar'),
                ('Pengukuran', 'list_pengukuran_pakar'),
                (f'Hapus {tanggal_ukur}', None),
            ]
        }
        return render(request, 'pakar_confirm_delete_pengukuran.html', context)
        
    except PengukuranFisik.DoesNotExist:
        messages.error(request, 'Pengukuran tidak ditemukan.')
        return redirect('list_pengukuran_pakar')


@login_required
@user_passes_test(is_expert)
def create_pasien_pakar(request):
    """
    View untuk membuat Pasien baru
    """
    if request.method == 'POST':
        # Terima data dari form
        nama_pengguna = request.POST.get('nama_pengguna')
        kata_sandi = request.POST.get('kata_sandi')
        nama = request.POST.get('nama')
        jenis_kelamin = request.POST.get('jenis_kelamin')
        tanggal_lahir = request.POST.get('tanggal_lahir')
        nama_wali = request.POST.get('nama_wali')
        nomor_telepon = request.POST.get('nomor_telepon')
        
        # Validasi data
        if not all([nama_pengguna, kata_sandi, nama, jenis_kelamin, tanggal_lahir]):
            return render(request, 'pakar_form_pasien.html', {
                'error': 'Field wajib harus diisi',
                'page_title': 'Tambah Pasien Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pasien', 'list_patients_pakar'),
                    ('Tambah Pasien', 'create_pasien_pakar'),
                ]
            })
        
        # Cek apakah nama pengguna sudah ada
        if Pasien.objects.filter(namaPengguna=nama_pengguna).exists():
            return render(request, 'pakar_form_pasien.html', {
                'error': 'Nama pengguna sudah digunakan',
                'page_title': 'Tambah Pasien Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pasien', 'list_patients_pakar'),
                    ('Tambah Pasien', 'create_pasien_pakar'),
                ]
            })
        
        try:
            # Buat objek Pasien baru
            pasien = Pasien(
                namaPengguna=nama_pengguna,
                nama=nama,
                jenisKelamin=jenis_kelamin,
                tanggalLahir=tanggal_lahir,
                namaWali=nama_wali or None,
                nomorTelepon=nomor_telepon or None
            )
            
            # PENTING: Sebelum menyimpan, panggil metode set_password pada objek Pasien
            pasien.set_password(kata_sandi)
            
            # Simpan objek Pasien
            pasien.save()
            
            # Redirect ke daftar pasien
            return redirect('list_patients_pakar')
            
        except Exception as e:
            return render(request, 'pakar_form_pasien.html', {
                'error': f'Terjadi kesalahan: {str(e)}',
                'page_title': 'Tambah Pasien Baru',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pasien', 'list_patients_pakar'),
                    ('Tambah Pasien', 'create_pasien_pakar'),
                ]
            })
    
    # Metode GET: Tampilkan form
    context = {
        'page_title': 'Tambah Pasien Baru',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Pasien', 'list_patients_pakar'),
            ('Tambah Pasien', 'create_pasien_pakar'),
        ]
    }
    
    return render(request, 'pakar_form_pasien.html', context)


@login_required
@user_passes_test(is_expert)
def edit_pasien_pakar(request, pasien_id):
    """
    View untuk mengedit Pasien
    """
    try:
        pasien = Pasien.objects.get(id=pasien_id)
    except Pasien.DoesNotExist:
        return render(request, 'pakar_list_patients.html', {
            'error': 'Pasien tidak ditemukan'
        })
    
    if request.method == 'POST':
        # Terima data dari form
        nama = request.POST.get('nama')
        jenis_kelamin = request.POST.get('jenis_kelamin')
        tanggal_lahir = request.POST.get('tanggal_lahir')
        nama_wali = request.POST.get('nama_wali')
        nomor_telepon = request.POST.get('nomor_telepon')
        kata_sandi_baru = request.POST.get('kata_sandi_baru')
        
        # Validasi data
        if not all([nama, jenis_kelamin, tanggal_lahir]):
            return render(request, 'pakar_form_pasien.html', {
                'pasien': pasien,
                'error': 'Field wajib harus diisi',
                'page_title': f'Edit Pasien: {pasien.nama}',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pasien', 'list_patients_pakar'),
                    (f'Edit {pasien.nama}', ''),
                ]
            })
        
        try:
            # Update data pasien
            pasien.nama = nama
            pasien.jenisKelamin = jenis_kelamin
            pasien.tanggalLahir = tanggal_lahir
            pasien.namaWali = nama_wali or None
            pasien.nomorTelepon = nomor_telepon or None
            
            # Jika ada kata sandi baru, update
            if kata_sandi_baru:
                if len(kata_sandi_baru) < 6:
                    return render(request, 'pakar_form_pasien.html', {
                        'pasien': pasien,
                        'error': 'Kata sandi minimal 6 karakter',
                        'page_title': f'Edit Pasien: {pasien.nama}',
                        'breadcrumb_items': [
                            ('Dashboard', 'dashboard_pakar'),
                            ('Pasien', 'list_patients_pakar'),
                            (f'Edit {pasien.nama}', ''),
                        ]
                    })
                pasien.set_password(kata_sandi_baru)
            
            # Simpan perubahan
            pasien.save()
            
            # Redirect ke daftar pasien
            return redirect('list_patients_pakar')
            
        except Exception as e:
            return render(request, 'pakar_form_pasien.html', {
                'pasien': pasien,
                'error': f'Terjadi kesalahan: {str(e)}',
                'page_title': f'Edit Pasien: {pasien.nama}',
                'breadcrumb_items': [
                    ('Dashboard', 'dashboard_pakar'),
                    ('Pasien', 'list_patients_pakar'),
                    (f'Edit {pasien.nama}', ''),
                ]
            })
    
    # Metode GET: Tampilkan form dengan data pasien
    context = {
        'pasien': pasien,
        'page_title': f'Edit Pasien: {pasien.nama}',
        'breadcrumb_items': [
            ('Dashboard', 'dashboard_pakar'),
            ('Pasien', 'list_patients_pakar'),
            (f'Edit {pasien.nama}', None),
        ]
    }
    
    return render(request, 'pakar_form_pasien.html', context)


@login_required
@user_passes_test(is_expert)
def delete_pasien_pakar(request, pasien_id):
    """
    View untuk menghapus Pasien
    """
    try:
        pasien = Pasien.objects.get(id=pasien_id)
        nama_pasien = pasien.nama
        
        if request.method == 'POST':
            # Hapus pasien
            pasien.delete()
            messages.success(request, f'Pasien "{nama_pasien}" berhasil dihapus.')
            return redirect('list_patients_pakar')
        
        # Metode GET: Tampilkan konfirmasi
        context = {
            'pasien': pasien,
            'page_title': f"Hapus Pasien: {nama_pasien}",
            'breadcrumb_items': [
                ('Dashboard', 'dashboard_pakar'),
                ('Pasien', 'list_patients_pakar'),
                (f'Hapus {nama_pasien}', None),
            ]
        }
        return render(request, 'pakar_confirm_delete_pasien.html', context)
        
    except Pasien.DoesNotExist:
        messages.error(request, 'Pasien tidak ditemukan.')
        return redirect('list_patients_pakar')


def riwayat_list(request):
    """
    View untuk menampilkan daftar riwayat pengukuran
    """
    # Pastikan pengguna adalah pasien
    if 'pasien_id' not in request.session:
        return redirect('login_pasien')
    
    # Dapatkan pasien_id dari session
    pasien_id = request.session['pasien_id']
    
    # Dapatkan daftar pengukuran untuk pasien tersebut, urutkan dari yang terbaru
    pengukuran_list = PengukuranFisik.objects.filter(pasien_id=pasien_id).order_by('-tanggalUkur')
    
    return render(request, 'riwayat_list.html', {
        'pengukuran_list': pengukuran_list
    })


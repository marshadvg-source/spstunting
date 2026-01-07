from django.db import models
from django.contrib.auth.models import User # Model Pengguna bawaan Django (untuk Admin/Pakar)
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.hashers import make_password, check_password

## =======================================================
## 1. DATA PENGGUNA DAN PASIEN
## =======================================================

class Pasien(models.Model):
    # Entitas Balita/Anak yang didiagnosa. Login dibuat sederhana terpisah dari User Django.
    
    # Kredensial Akses Sederhana (untuk Pasien/Wali)
    namaPengguna = models.CharField(max_length=50, unique=True, help_text="Nama Pengguna untuk akses Pasien/Wali")
    kataSandi = models.CharField(max_length=128) # Catatan: Gunakan fungsi hash saat menyimpan!

    # Data Diri Balita/Anak
    nama = models.CharField(max_length=100)
    jenisKelamin = models.CharField(max_length=10, choices=[('L', 'Laki-laki'), ('P', 'Perempuan')])
    tanggalLahir = models.DateField()

    # Data Wali (Opsional)
    namaWali = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nama Wali/Orang Tua")
    nomorTelepon = models.CharField(max_length=15, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Pasien"

    def __str__(self):
        return f"Pasien: {self.nama} ({self.namaPengguna})"
    
    def set_password(self, raw_password):
        """Method to set hashed password"""
        self.kataSandi = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Method to check password"""
        return check_password(raw_password, self.kataSandi)
    
    @property
    def usia_sekarang(self):
        """Menghitung usia pasien dalam bulan dari tanggal lahir ke tanggal sekarang"""
        from datetime import date
        today = date.today()
        usia_bulan = (today.year - self.tanggalLahir.year) * 12 + (today.month - self.tanggalLahir.month)
        # Jika hari dalam bulan ini lebih kecil dari hari lahir, kurangi satu bulan
        if today.day < self.tanggalLahir.day:
            usia_bulan -= 1
        return usia_bulan

# Catatan: Administrator dan Pakar/Nakes menggunakan model User bawaan Django.

## =======================================================
## 2. BASIS PENGETAHUAN (Knowledge Base)
## =======================================================

class Gejala(models.Model):
    kodeGejala = models.CharField(max_length=10, primary_key=True)
    namaGejala = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Gejala"

    def __str__(self):
        return f"{self.kodeGejala}: {self.namaGejala}"

class Kondisi(models.Model):
    kodeKondisi = models.CharField(max_length=10, primary_key=True)
    namaKondisi = models.CharField(max_length=255)
    deskripsi = models.TextField()
    solusi = models.TextField()

    class Meta:
        verbose_name_plural = "Kondisi"

    def __str__(self):
        return f"{self.kodeKondisi}: {self.namaKondisi}"

class Aturan(models.Model):
    # Entitas untuk Aturan IF-THEN. Merepresentasikan relasi KONDISI (THEN) dan GEJALA (IF)
    kondisi = models.ForeignKey(Kondisi, on_delete=models.CASCADE)
    gejala = models.ForeignKey(Gejala, on_delete=models.CASCADE)
    
    # KelompokAturan: PENTING untuk logika AND/OR.
    # Semua gejala dalam satu KelompokAturan (misal R01) harus terpenuhi (AND).
    kodeKelompokAturan = models.CharField(max_length=10, help_text="Kode Kelompok Aturan (misal: R01).")
    keterangan = models.TextField(blank=True, null=True)

    class Meta:
        # Memastikan tidak ada duplikasi Gejala dalam satu KelompokAturan Kondisi tertentu
        unique_together = ('kondisi', 'gejala', 'kodeKelompokAturan')
        verbose_name_plural = "Aturan Basis Pengetahuan"

    def __str__(self):
        return f"Aturan {self.kodeKelompokAturan}: JIKA {self.gejala.kodeGejala} MAKA {self.kondisi.kodeKondisi}"

## =======================================================
## 3. PENCATATAN KONSULTASI (Input/Output Mesin Inferensi)
## =======================================================

class Konsultasi(models.Model):
    pasien = models.ForeignKey(Pasien, on_delete=models.CASCADE)
    tanggalKonsultasi = models.DateTimeField(auto_now_add=True)
    
    # Hasil akhir diagnosa (Output Mesin Inferensi)
    hasilKondisi = models.ForeignKey(Kondisi, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Hasil Diagnosa")

    class Meta:
        verbose_name_plural = "Konsultasi"

    def __str__(self):
        return f"Konsultasi {self.id} oleh {self.pasien.nama} ({self.tanggalKonsultasi.date()})"

class DetailKonsultasi(models.Model):
    konsultasi = models.ForeignKey(Konsultasi, on_delete=models.CASCADE)
    # Gejala yang dipilih/dimasukkan oleh pengguna (Input Mesin Inferensi)
    gejala = models.ForeignKey(Gejala, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('konsultasi', 'gejala')
        verbose_name_plural = "Detail Konsultasi"

    def __str__(self):
        return f"Konsultasi {self.konsultasi.id} - Gejala: {self.gejala.kodeGejala}"

## =======================================================
## 4. PENGUKURAN FISIK & GRAFIK (Data Stunting)
## =======================================================

class PengukuranFisik(models.Model):
    # Digunakan untuk mencatat data klinis antropometri periodik
    pasien = models.ForeignKey(Pasien, on_delete=models.CASCADE)
    tanggalUkur = models.DateField()
    beratBadan = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Berat Badan (kg)") 
    tinggiBadan = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Tinggi/Panjang Badan (cm)") 
    
    # Tambahan field untuk data Posyandu
    lingkarKepala = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Lingkar Kepala (cm)")
    lingkarLengan = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Lingkar Lengan Atas (cm)")
    imunisasi = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Imunisasi")
    
    # Kolom untuk menyimpan hasil perhitungan Z-Score
    skor_Z_BB_U = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Z-Score BB/U")
    skor_Z_TB_U = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Z-Score TB/U")
    
    class Meta:
        ordering = ['tanggalUkur']
        verbose_name_plural = "Pengukuran Fisik"
    
    def __str__(self):
        return f"Pengukuran {self.pasien.nama} pada {self.tanggalUkur}"

## =======================================================
## 5. NOTIFIKASI
## =======================================================

class Notifikasi(models.Model):
    # Digunakan untuk pengingat jadwal pengukuran ulang atau info gizi
    pasien = models.ForeignKey(Pasien, on_delete=models.CASCADE)
    judul = models.CharField(max_length=255)
    pesan = models.TextField()
    jadwalNotifikasi = models.DateTimeField() # Kapan notifikasi harus muncul
    sudahTerkirim = models.BooleanField(default=False, verbose_name="Sudah Dibaca") 
    tipe = models.CharField(max_length=50, default='pengukuran_ulang') 

    class Meta:
        ordering = ['-jadwalNotifikasi']
        verbose_name_plural = "Daftar Notifikasi"
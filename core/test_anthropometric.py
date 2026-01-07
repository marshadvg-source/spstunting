from .utils import hitung_dan_simpan_zscore, buat_jadwal_notifikasi
from .models import Pasien, PengukuranFisik
from datetime import date, timedelta

def test_zscore_calculation():
    # Create a test patient
    pasien = Pasien(
        namaPengguna="testuser",
        nama="Test User",
        jenisKelamin="L",
        tanggalLahir=date(2020, 1, 1)
    )
    pasien.set_password("testpassword")
    pasien.save()
    
    # Create a test measurement
    pengukuran = PengukuranFisik.objects.create(
        pasien=pasien,
        tanggalUkur=date(2021, 1, 1),
        beratBadan=12.5,
        tinggiBadan=85.0
    )
    
    print(f"Created measurement for {pasien.nama}")
    print(f"Date: {pengukuran.tanggalUkur}")
    print(f"Weight: {pengukuran.beratBadan} kg")
    print(f"Height: {pengukuran.tinggiBadan} cm")
    print(f"Initial Z-scores - Weight: {pengukuran.skor_Z_BB_U}, Height: {pengukuran.skor_Z_TB_U}")
    
    # Calculate Z-scores
    updated_pengukuran = hitung_dan_simpan_zscore(pengukuran.id)
    
    print(f"Calculated Z-scores - Weight: {updated_pengukuran.skor_Z_BB_U}, Height: {updated_pengukuran.skor_Z_TB_U}")
    
    # Test notification scheduling
    notifikasi = buat_jadwal_notifikasi(pasien.id, pengukuran.tanggalUkur)
    print(f"Scheduled notification for: {notifikasi.jadwalNotifikasi}")
    
    # Clean up
    notifikasi.delete()
    pengukuran.delete()
    pasien.delete()
    
    print("Test completed successfully!")

if __name__ == "__main__":
    test_zscore_calculation()
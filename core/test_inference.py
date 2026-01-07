from .views import jalankan_inferensi
from .models import Pasien

def test_inference_engine():
    # Get the first patient (created in sample data)
    pasien = Pasien.objects.first()
    
    if not pasien:
        print("No patient found in database!")
        return
    
    print(f"Testing inference engine for patient: {pasien.nama}")
    
    # Test case 1: Symptoms indicating stunting
    kode_gejala_stunting = ["G01", "G02"]  # Height and weight below normal
    print(f"\nTest Case 1: Symptoms {kode_gejala_stunting} (Indicating Stunting)")
    
    konsultasi_stunting = jalankan_inferensi(pasien.id, kode_gejala_stunting)
    print(f"Diagnosis Result: {konsultasi_stunting.hasilKondisi.namaKondisi}")
    print(f"Condition Code: {konsultasi_stunting.hasilKondisi.kodeKondisi}")
    
    # Test case 2: Symptoms indicating normal condition
    kode_gejala_normal = ["G02", "G03", "G05"]  # Weight normal, good appetite, normal motor development
    print(f"\nTest Case 2: Symptoms {kode_gejala_normal} (Indicating Normal)")
    
    konsultasi_normal = jalankan_inferensi(pasien.id, kode_gejala_normal)
    print(f"Diagnosis Result: {konsultasi_normal.hasilKondisi.namaKondisi}")
    print(f"Condition Code: {konsultasi_normal.hasilKondisi.kodeKondisi}")
    
    # Test case 3: Insufficient symptoms
    kode_gejala_insufficient = ["G01"]  # Only height below normal
    print(f"\nTest Case 3: Symptoms {kode_gejala_insufficient} (Insufficient for Diagnosis)")
    
    konsultasi_insufficient = jalankan_inferensi(pasien.id, kode_gejala_insufficient)
    if konsultasi_insufficient.hasilKondisi:
        print(f"Diagnosis Result: {konsultasi_insufficient.hasilKondisi.namaKondisi}")
    else:
        print("No diagnosis - insufficient symptoms to match any rule group")

if __name__ == "__main__":
    test_inference_engine()
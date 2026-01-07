from .models import Pasien

def test_password_hashing():
    # Create a new patient with password
    pasien = Pasien(
        namaPengguna="testuser",
        nama="Test User",
        jenisKelamin="L",
        tanggalLahir="2020-01-01"
    )
    pasien.set_password("testpassword")
    pasien.save()
    
    print(f"Created patient: {pasien.namaPengguna}")
    print(f"Password hash: {pasien.kataSandi}")
    
    # Test password checking
    if pasien.check_password("testpassword"):
        print("Password verification: SUCCESS")
    else:
        print("Password verification: FAILED")
    
    if pasien.check_password("wrongpassword"):
        print("Wrong password test: FAILED")
    else:
        print("Wrong password test: SUCCESS")
    
    # Clean up
    pasien.delete()

if __name__ == "__main__":
    test_password_hashing()
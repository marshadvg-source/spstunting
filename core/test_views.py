from django.test import TestCase, Client
from django.urls import reverse
from .models import Pasien, PengukuranFisik
from datetime import date

class AuthViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a test patient
        self.pasien = Pasien(
            namaPengguna="testuser",
            nama="Test User",
            jenisKelamin="L",
            tanggalLahir="2020-01-01"
        )
        self.pasien.set_password("testpassword")
        self.pasien.save()
    
    def test_registration_page(self):
        response = self.client.get(reverse('registrasi_pasien'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registrasi Pasien")
    
    def test_login_page(self):
        response = self.client.get(reverse('login_pasien'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Login Pasien")
    
    def test_successful_login(self):
        response = self.client.post(reverse('login_pasien'), {
            'nama_pengguna': 'testuser',
            'kata_sandi': 'testpassword'
        })
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        self.assertRedirects(response, reverse('dashboard_pasien'))
    
    def test_failed_login(self):
        response = self.client.post(reverse('login_pasien'), {
            'nama_pengguna': 'testuser',
            'kata_sandi': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nama pengguna atau kata sandi salah")
    
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard_pasien'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        # Just check that it redirects to login page
        self.assertRedirects(response, reverse('login_pasien'), fetch_redirect_response=False)
    
    def test_dashboard_after_login(self):
        # Login first
        self.client.post(reverse('login_pasien'), {
            'nama_pengguna': 'testuser',
            'kata_sandi': 'testpassword'
        })
        
        # Now access dashboard
        response = self.client.get(reverse('dashboard_pasien'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "selamat datang")
        self.assertContains(response, "Test User")


class AnthropometricViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a test patient
        self.pasien = Pasien(
            namaPengguna="testuser",
            nama="Test User",
            jenisKelamin="L",
            tanggalLahir="2020-01-01"
        )
        self.pasien.set_password("testpassword")
        self.pasien.save()
        
        # Login the patient
        self.client.post(reverse('login_pasien'), {
            'nama_pengguna': 'testuser',
            'kata_sandi': 'testpassword'
        })
    
    def test_input_pengukuran_page(self):
        response = self.client.get(reverse('input_pengukuran'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Input Pengukuran Fisik")
    
    def test_input_pengukuran_post(self):
        response = self.client.post(reverse('input_pengukuran'), {
            'tanggal_ukur': '2021-01-01',
            'berat_badan': '12.5',
            'tinggi_badan': '85.0'
        })
        
        # Check that measurement was created
        measurements = PengukuranFisik.objects.all()
        self.assertEqual(measurements.count(), 1)
        
        measurement = measurements.first()
        self.assertEqual(float(measurement.beratBadan), 12.5)
        self.assertEqual(float(measurement.tinggiBadan), 85.0)
        self.assertIsNotNone(measurement.skor_Z_BB_U)
        self.assertIsNotNone(measurement.skor_Z_TB_U)
    
    def test_graph_page(self):
        # Create a test measurement
        PengukuranFisik.objects.create(
            pasien=self.pasien,
            tanggalUkur=date(2021, 1, 1),
            beratBadan=12.5,
            tinggiBadan=85.0
        )
        
        response = self.client.get(reverse('tampilkan_grafik_riwayat', kwargs={'pasien_id': self.pasien.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Grafik Riwayat Pengukuran Z-Score")
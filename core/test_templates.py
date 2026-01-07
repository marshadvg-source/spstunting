from django.test import TestCase, Client
from django.urls import reverse
from .models import Pasien

class TemplateIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
    
    def test_base_template_used(self):
        # Test that the home page uses the base template
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        # Check that Bootstrap CSS is included
        self.assertContains(response, 'bootstrap')
        # Check that the title block is working
        self.assertContains(response, 'Sistem Diagnosa Stunting')
    
    def test_patient_navigation_shown_when_logged_in(self):
        # Create a test patient
        pasien = Pasien(
            namaPengguna="testuser",
            nama="Test User",
            jenisKelamin="L",
            tanggalLahir="2020-01-01"
        )
        pasien.set_password("testpassword")
        pasien.save()
        
        # Login the patient
        self.client.post(reverse('login_pasien'), {
            'nama_pengguna': 'testuser',
            'kata_sandi': 'testpassword'
        })
        
        # Check that patient navigation is shown
        response = self.client.get(reverse('dashboard_pasien'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Menu Pasien')
        self.assertContains(response, 'Dashboard')
        self.assertContains(response, 'Input Pengukuran')
        self.assertContains(response, 'Diagnosa Stunting')
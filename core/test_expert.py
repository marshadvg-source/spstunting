from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Pasien, Kondisi, Gejala, Aturan

class ExpertViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create an expert/staff user
        self.expert = User.objects.create_user(
            username='pakar',
            password='password123',
            is_staff=True
        )
        self.expert.save()
        
        # Create a regular user (non-staff)
        self.regular_user = User.objects.create_user(
            username='regular',
            password='password123',
            is_staff=False
        )
        self.regular_user.save()
        
        # Create a patient
        self.pasien = Pasien.objects.create(
            namaPengguna="testpasien",
            nama="Test Pasien",
            jenisKelamin="L",
            tanggalLahir="2020-01-01"
        )
        self.pasien.set_password("testpassword")
        self.pasien.save()
        
        # Create sample conditions
        self.kondisi1 = Kondisi.objects.create(
            kodeKondisi="K01",
            namaKondisi="Stunting Sedang",
            deskripsi="Anak mengalami gangguan pertumbuhan",
            solusi="Perbaiki pola makan"
        )
        
        self.kondisi2 = Kondisi.objects.create(
            kodeKondisi="K02",
            namaKondisi="Normal",
            deskripsi="Pertumbuhan normal",
            solusi="Pertahankan pola makan"
        )
        
        # Create sample symptoms
        self.gejala1 = Gejala.objects.create(
            kodeGejala="G01",
            namaGejala="Tinggi badan kurang dari normal"
        )
        
        self.gejala2 = Gejala.objects.create(
            kodeGejala="G02",
            namaGejala="Berat badan kurang dari normal"
        )
        
        self.gejala3 = Gejala.objects.create(
            kodeGejala="G03",
            namaGejala="Nafsu makan rendah"
        )

    def test_expert_can_access_create_rule_group(self):
        # Login as expert
        self.client.login(username='pakar', password='password123')
        
        # Access the create rule group page
        response = self.client.get(reverse('create_rule_group'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Buat Kelompok Aturan Baru")

    def test_regular_user_cannot_access_create_rule_group(self):
        # Login as regular user
        self.client.login(username='regular', password='password123')
        
        # Try to access the create rule group page
        response = self.client.get(reverse('create_rule_group'))
        # Should be redirected to login or denied access
        self.assertIn(response.status_code, [302, 403])

    def test_non_logged_in_user_cannot_access_create_rule_group(self):
        # Try to access the create rule group page without logging in
        response = self.client.get(reverse('create_rule_group'))
        # Should be redirected to login
        self.assertEqual(response.status_code, 302)

    def test_expert_can_create_rule_group(self):
        # Login as expert
        self.client.login(username='pakar', password='password123')
        
        # Post data to create a rule group
        response = self.client.post(reverse('create_rule_group'), {
            'kondisi': 'K01',
            'kode_kelompok': 'R01',
            'gejala': ['G01', 'G02']
        })
        
        # Should redirect to list rules page
        self.assertEqual(response.status_code, 302)
        
        # Check that rules were created
        rules = Aturan.objects.filter(kodeKelompokAturan='R01')
        self.assertEqual(rules.count(), 2)
        
        # Check that both symptoms are associated with the condition
        gejala_kodes = [rule.gejala.kodeGejala for rule in rules]
        self.assertIn('G01', gejala_kodes)
        self.assertIn('G02', gejala_kodes)

    def test_expert_can_list_patients(self):
        # Login as expert
        self.client.login(username='pakar', password='password123')
        
        # Access the list patients page
        response = self.client.get(reverse('list_patients_pakar'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Pasien")

    def test_expert_can_view_patient_details(self):
        # Login as expert
        self.client.login(username='pakar', password='password123')
        
        # Access the patient detail page
        response = self.client.get(reverse('detail_pasien_pakar', kwargs={'pasien_id': self.pasien.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Pasien")

    def test_expert_can_list_rules(self):
        # Create a sample rule
        Aturan.objects.create(
            kondisi=self.kondisi1,
            gejala=self.gejala1,
            kodeKelompokAturan='R01'
        )
        
        # Login as expert
        self.client.login(username='pakar', password='password123')
        
        # Access the list rules page
        response = self.client.get(reverse('list_rules_pakar'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "R01")
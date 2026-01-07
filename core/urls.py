from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    # Homepage
    path('', views.home, name='home'),
    
    # Authentication paths
    path('registrasi/', views.registrasi_pasien, name='registrasi_pasien'),
    path('login/', views.login_pasien, name='login_pasien'),
    path('pakar/login/', views.login_pakar, name='login_pakar'),  # Expert login path
    path('pakar/logout/', views.logout_pakar, name='logout_pakar'),
    path('logout/', views.logout_pasien, name='logout_pasien'),
    path('dashboard/', views.dashboard_pasien, name='dashboard_pasien'),
    path('akun/edit/', views.edit_akun_pasien, name='edit_akun_pasien'),
    
    # Anthropometric measurement paths
    path('pengukuran/input/', views.input_pengukuran, name='input_pengukuran'),
    
    # Paths for diagnosis
    path('diagnosa/', views.form_diagnosa, name='form_diagnosa'),
    path('diagnosa/hasil/<int:konsultasi_id>/', views.tampilkan_hasil_diagnosa, name='tampilkan_hasil_diagnosa'),
    
    # Paths for anthropometric data and notifications
    path('grafik/<int:pasien_id>/', views.tampilkan_grafik_riwayat, name='tampilkan_grafik_riwayat'),
    path('riwayat/', views.riwayat_pengukuran, name='riwayat_pengukuran'),
    path('riwayat/list/', views.riwayat_list, name='riwayat_list'),
    path('riwayat/pdf/', views.cetak_riwayat_pdf, name='cetak_riwayat_pdf'),
    path('diagnosa/preview/', views.preview_diagnosa, name='preview_diagnosa'),
    path('diagnosa/hasil/<int:konsultasi_id>/pdf/', views.cetak_hasil_diagnosa_pdf, name='cetak_hasil_diagnosa_pdf'),
    # Expert/Admin paths
    path('pakar/dashboard/', views.dashboard_pakar, name='dashboard_pakar'),
    path('pakar/help/', views.pakar_help, name='pakar_help'),
    path('pakar/rules/create/', views.create_rule_group, name='create_rule_group'),
    path('pakar/patients/', views.list_patients_pakar, name='list_patients_pakar'),
    path('pakar/patients/<int:pasien_id>/', views.detail_pasien_pakar, name='detail_pasien_pakar'),
    path('pakar/patients/create/', views.create_pasien_pakar, name='create_pasien_pakar'),
    path('pakar/patients/<int:pasien_id>/edit/', views.edit_pasien_pakar, name='edit_pasien_pakar'),
    path('pakar/patients/<int:pasien_id>/delete/', views.delete_pasien_pakar, name='delete_pasien_pakar'),
    path('pakar/rules/', views.list_rules_pakar, name='list_rules_pakar'),
    path('pakar/rules/<str:pk>/detail/', views.show_rule_detail, name='show_rule_detail'),
    path('pakar/rules/<str:pk>/edit/', views.edit_rule_pakar, name='edit_rule_pakar'),
    path('pakar/rules/<str:pk>/delete/', views.delete_rule_pakar, name='delete_rule_pakar'),
    
    # Pengukuran (Measurement) management paths
    path('pakar/pengukuran/', views.list_pengukuran_pakar, name='list_pengukuran_pakar'),
    path('pakar/pengukuran/create/', views.create_pengukuran_pakar, name='create_pengukuran_pakar'),
    path('pakar/pengukuran/<int:pk>/edit/', views.edit_pengukuran_pakar, name='edit_pengukuran_pakar'),
    path('pakar/pengukuran/<int:pk>/delete/', views.delete_pengukuran_pakar, name='delete_pengukuran_pakar'),
    
    # Gejala (Symptom) management paths
    path('pakar/gejala/', views.list_gejala_pakar, name='list_gejala_pakar'),
    path('pakar/gejala/create/', views.create_gejala_pakar, name='create_gejala_pakar'),
    path('pakar/gejala/<str:pk>/edit/', views.edit_gejala_pakar, name='edit_gejala_pakar'),
    path('pakar/gejala/<str:pk>/delete/', views.delete_gejala_pakar, name='delete_gejala_pakar'),
    
    # Kondisi (Condition) management paths
    path('pakar/kondisi/', views.list_kondisi_pakar, name='list_kondisi_pakar'),
    path('pakar/kondisi/create/', views.create_kondisi_pakar, name='create_kondisi_pakar'),
    path('pakar/kondisi/<str:pk>/edit/', views.edit_kondisi_pakar, name='edit_kondisi_pakar'),
    path('pakar/kondisi/<str:pk>/delete/', views.delete_kondisi_pakar, name='delete_kondisi_pakar'),
    
    # Notification paths
    path('notifikasi/', views.daftar_notifikasi, name='daftar_notifikasi'),
]
from django.contrib import admin
from django.http import HttpResponseForbidden
from django.utils.html import format_html
from django.urls import reverse
from .models import Pasien, Gejala, Kondisi, Aturan, Konsultasi, DetailKonsultasi, PengukuranFisik, Notifikasi

# Custom ModelAdmin classes with role-based access control
class RestrictedModelAdmin(admin.ModelAdmin):
    """
    Base ModelAdmin class that restricts access to only Pakar Diagnosa group members
    Superusers (Admin) are not allowed to access these models
    """
    def has_module_permission(self, request):
        # Allow access only if user is staff and belongs to "Pakar Diagnosa" group
        # Superusers (Admin) are not allowed to access KB models
        if request.user.is_authenticated and request.user.is_staff:
            # Check if user is NOT a superuser (admins are superusers)
            # Only non-superusers who are in Pakar Diagnosa group can access
            if not request.user.is_superuser and request.user.groups.filter(name='Pakar Diagnosa').exists():
                return True
        return False
    
    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)
    
    def has_add_permission(self, request):
        return self.has_module_permission(request)
    
    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)
    
    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)

# Register models with restricted access for knowledge base models
@admin.register(Gejala)
class GejalaAdmin(RestrictedModelAdmin):
    list_display = ('kodeGejala', 'namaGejala')
    search_fields = ('kodeGejala', 'namaGejala')
    ordering = ('kodeGejala',)

@admin.register(Kondisi)
class KondisiAdmin(RestrictedModelAdmin):
    list_display = ('kodeKondisi', 'namaKondisi')
    search_fields = ('kodeKondisi', 'namaKondisi')
    ordering = ('kodeKondisi',)

@admin.register(Aturan)
class AturanAdmin(RestrictedModelAdmin):
    list_display = ('kodeKelompokAturan', 'kondisi', 'gejala')
    list_filter = ('kodeKelompokAturan', 'kondisi')
    search_fields = ('kodeKelompokAturan', 'kondisi__namaKondisi', 'gejala__namaGejala')
    ordering = ('kodeKelompokAturan', 'kondisi', 'gejala')

# Register other models with default access (accessible by both Admin and Pakar)
@admin.register(Pasien)
class PasienAdmin(admin.ModelAdmin):
    list_display = ('nama', 'namaPengguna', 'jenisKelamin', 'tanggalLahir', 'namaWali')
    list_filter = ('jenisKelamin', 'tanggalLahir')
    search_fields = ('nama', 'namaPengguna', 'namaWali')
    ordering = ('nama',)

@admin.register(Konsultasi)
class KonsultasiAdmin(admin.ModelAdmin):
    list_display = ('id', 'pasien', 'tanggalKonsultasi', 'hasilKondisi', 'tombol_cetak_pdf')
    list_filter = ('tanggalKonsultasi', 'hasilKondisi')
    search_fields = ('pasien__nama', 'hasilKondisi__namaKondisi')
    ordering = ('-tanggalKonsultasi',)
    date_hierarchy = 'tanggalKonsultasi'
    
    def tombol_cetak_pdf(self, obj):
        return format_html(
            '<a class="button" href="/diagnosa/hasil/{}/pdf/" target="_blank" '
            'style="background-color: #d9534f; color: white; padding: 5px 10px; '
            'border-radius: 4px; text-decoration: none;">Cetak PDF</a>',
            obj.id
        )
    tombol_cetak_pdf.short_description = 'Aksi Cetak'
    tombol_cetak_pdf.allow_tags = True

@admin.register(DetailKonsultasi)
class DetailKonsultasiAdmin(admin.ModelAdmin):
    list_display = ('konsultasi', 'gejala')
    list_filter = ('gejala',)
    search_fields = ('konsultasi__pasien__nama', 'gejala__namaGejala')

@admin.register(PengukuranFisik)
class PengukuranFisikAdmin(admin.ModelAdmin):
    list_display = ('pasien', 'tanggalUkur', 'beratBadan', 'tinggiBadan', 'skor_Z_BB_U', 'skor_Z_TB_U', 'tombol_cetak_riwayat')
    list_filter = ('tanggalUkur', 'pasien__jenisKelamin')
    search_fields = ('pasien__nama',)
    ordering = ('-tanggalUkur',)
    date_hierarchy = 'tanggalUkur'
    
    def tombol_cetak_riwayat(self, obj):
        return format_html(
            '<a class="button" href="/riwayat/pdf/?pasien_id={}" target="_blank" '
            'style="background-color: #d9534f; color: white; padding: 5px 10px; '
            'border-radius: 4px; text-decoration: none;">Cetak Riwayat</a>',
            obj.pasien.id
        )
    tombol_cetak_riwayat.short_description = 'Aksi Cetak'
    tombol_cetak_riwayat.allow_tags = True

@admin.register(Notifikasi)
class NotifikasiAdmin(admin.ModelAdmin):
    list_display = ('pasien', 'judul', 'jadwalNotifikasi', 'sudahTerkirim', 'tipe')
    list_filter = ('sudahTerkirim', 'tipe', 'jadwalNotifikasi')
    search_fields = ('pasien__nama', 'judul')
    ordering = ('-jadwalNotifikasi',)
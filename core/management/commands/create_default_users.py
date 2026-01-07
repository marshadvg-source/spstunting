from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import Pasien, Konsultasi, DetailKonsultasi, Gejala, Kondisi, Aturan, PengukuranFisik

class Command(BaseCommand):
    help = 'Create default users and groups for the SP Stunting system'

    def handle(self, *args, **options):
        # Create Groups
        admin_group, created = Group.objects.get_or_create(name='Admin System')
        if created:
            self.stdout.write(self.style.SUCCESS('Created group: Admin System'))
        else:
            self.stdout.write(self.style.WARNING('Group Admin System already exists'))

        expert_group, created = Group.objects.get_or_create(name='Pakar Diagnosa')
        if created:
            self.stdout.write(self.style.SUCCESS('Created group: Pakar Diagnosa'))
        else:
            self.stdout.write(self.style.WARNING('Group Pakar Diagnosa already exists'))

        # Assign permissions to Admin System group (full access to all models)
        admin_permissions = Permission.objects.all()
        admin_group.permissions.set(admin_permissions)
        self.stdout.write(self.style.SUCCESS('Assigned all permissions to Admin System group'))

        # Assign permissions to Pakar Diagnosa group (limited access to patient data and full access to KB)
        # Get content types for core models
        pasien_ct = ContentType.objects.get_for_model(Pasien)
        konsultasi_ct = ContentType.objects.get_for_model(Konsultasi)
        detail_konsultasi_ct = ContentType.objects.get_for_model(DetailKonsultasi)
        gejala_ct = ContentType.objects.get_for_model(Gejala)
        kondisi_ct = ContentType.objects.get_for_model(Kondisi)
        aturan_ct = ContentType.objects.get_for_model(Aturan)
        pengukuran_ct = ContentType.objects.get_for_model(PengukuranFisik)

        # Permissions for Pakar Diagnosa group (view, add, change for patient data but NOT delete)
        # Full access to knowledge base models (Gejala, Kondisi, Aturan)
        pakar_permissions = [
            # Pasien permissions (view, add, change but NOT delete)
            Permission.objects.get(content_type=pasien_ct, codename='view_pasien'),
            Permission.objects.get(content_type=pasien_ct, codename='add_pasien'),
            Permission.objects.get(content_type=pasien_ct, codename='change_pasien'),
            
            # Konsultasi permissions
            Permission.objects.get(content_type=konsultasi_ct, codename='view_konsultasi'),
            Permission.objects.get(content_type=konsultasi_ct, codename='change_konsultasi'),
            Permission.objects.get(content_type=konsultasi_ct, codename='add_konsultasi'),
            
            # DetailKonsultasi permissions
            Permission.objects.get(content_type=detail_konsultasi_ct, codename='view_detailkonsultasi'),
            Permission.objects.get(content_type=detail_konsultasi_ct, codename='change_detailkonsultasi'),
            Permission.objects.get(content_type=detail_konsultasi_ct, codename='add_detailkonsultasi'),
            
            # Gejala permissions (full management)
            Permission.objects.get(content_type=gejala_ct, codename='view_gejala'),
            Permission.objects.get(content_type=gejala_ct, codename='change_gejala'),
            Permission.objects.get(content_type=gejala_ct, codename='add_gejala'),
            Permission.objects.get(content_type=gejala_ct, codename='delete_gejala'),
            
            # Kondisi permissions (full management)
            Permission.objects.get(content_type=kondisi_ct, codename='view_kondisi'),
            Permission.objects.get(content_type=kondisi_ct, codename='change_kondisi'),
            Permission.objects.get(content_type=kondisi_ct, codename='add_kondisi'),
            Permission.objects.get(content_type=kondisi_ct, codename='delete_kondisi'),
            
            # Aturan permissions (full management)
            Permission.objects.get(content_type=aturan_ct, codename='view_aturan'),
            Permission.objects.get(content_type=aturan_ct, codename='change_aturan'),
            Permission.objects.get(content_type=aturan_ct, codename='add_aturan'),
            Permission.objects.get(content_type=aturan_ct, codename='delete_aturan'),
            
            # PengukuranFisik permissions
            Permission.objects.get(content_type=pengukuran_ct, codename='view_pengukuranfisik'),
            Permission.objects.get(content_type=pengukuran_ct, codename='change_pengukuranfisik'),
            Permission.objects.get(content_type=pengukuran_ct, codename='add_pengukuranfisik'),
        ]

        # Clear existing permissions and set new ones for Pakar Diagnosa group
        expert_group.permissions.set(pakar_permissions)
        self.stdout.write(self.style.SUCCESS('Assigned appropriate permissions to Pakar Diagnosa group'))

        # Create Admin User (Superuser)
        admin_user, created = User.objects.get_or_create(username='admin')
        if created:
            admin_user.set_password('admin123')
            admin_user.is_staff = True
            admin_user.is_superuser = True  # Admin is superuser
            admin_user.save()
            admin_user.groups.add(admin_group)
            self.stdout.write(self.style.SUCCESS('Created admin user: admin/admin123 (Superuser)'))
        else:
            self.stdout.write(self.style.WARNING('Admin user already exists'))

        # Create Expert User (Staff but NOT superuser)
        expert_user, created = User.objects.get_or_create(username='pakar')
        if created:
            expert_user.set_password('pakar123')
            expert_user.is_staff = True       # Expert is staff
            expert_user.is_superuser = False  # Expert is NOT superuser
            expert_user.save()
            expert_user.groups.add(expert_group)
            self.stdout.write(self.style.SUCCESS('Created expert user: pakar/pakar123 (Staff, NOT Superuser)'))
        else:
            self.stdout.write(self.style.WARNING('Expert user already exists'))

        self.stdout.write(self.style.SUCCESS('Default users and groups setup completed successfully!'))
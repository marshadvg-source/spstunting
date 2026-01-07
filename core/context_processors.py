from .models import Notifikasi
from django.utils import timezone

def notifikasi_processor(request):
    pasien_id = request.session.get('pasien_id')
    if pasien_id:
        count = Notifikasi.objects.filter(
            pasien_id=pasien_id,
            sudahTerkirim=False,
            jadwalNotifikasi__lte=timezone.now()
        ).count()
        return {'notif_count': count}
    return {'notif_count': 0}
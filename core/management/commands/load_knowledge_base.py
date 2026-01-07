from django.core.management.base import BaseCommand
from core.models import Gejala, Kondisi, Aturan

class Command(BaseCommand):
    help = 'Load knowledge base data (conditions, symptoms, and rules) into the database'

    def handle(self, *args, **options):
        # Clear existing data
        Gejala.objects.all().delete()
        Kondisi.objects.all().delete()
        Aturan.objects.all().delete()
        
        self.stdout.write('Existing knowledge base data cleared.')
        
        # Define symptoms (25 Gejala)
        gejala_data = [
            {"kodeGejala": "G01", "namaGejala": "Tinggi badan sangat pendek"},
            {"kodeGejala": "G02", "namaGejala": "Berat badan sangat rendah"},
            {"kodeGejala": "G03", "namaGejala": "Nafsu makan sangat buruk"},
            {"kodeGejala": "G04", "namaGejala": "Sering sakit (infeksi berulang)"},
            {"kodeGejala": "G05", "namaGejala": "Perkembangan motorik lambat"},
            {"kodeGejala": "G06", "namaGejala": "Kulit keriput dan kering"},
            {"kodeGejala": "G07", "namaGejala": "Rambut tipis, jarang, mudah rontok"},
            {"kodeGejala": "G08", "namaGejala": "Edema (pembengkakan) di tubuh"},
            {"kodeGejala": "G09", "namaGejala": "Demam berulang"},
            {"kodeGejala": "G10", "namaGejala": "Frekuensi makan rendah"},
            {"kodeGejala": "G11", "namaGejala": "Asupan protein kurang"},
            {"kodeGejala": "G12", "namaGejala": "Asupan kalori kurang"},
            {"kodeGejala": "G13", "namaGejala": "Infeksi saluran pernapasan berulang"},
            {"kodeGejala": "G14", "namaGejala": "Penurunan berat badan drastis"},
            {"kodeGejala": "G15", "namaGejala": "Lemah dan lesu"},
            {"kodeGejala": "G16", "namaGejala": "Gangguan tidur"},
            {"kodeGejala": "G17", "namaGejala": "Gangguan perilaku makan"},
            {"kodeGejala": "G18", "namaGejala": "Muntah setelah makan"},
            {"kodeGejala": "G19", "namaGejala": "Diare kronis"},
            {"kodeGejala": "G20", "namaGejala": "Tidak mau makan"},
            {"kodeGejala": "G21", "namaGejala": "Tinggi badan normal"},
            {"kodeGejala": "G22", "namaGejala": "Berat badan normal"},
            {"kodeGejala": "G23", "namaGejala": "Nafsu makan baik"},
            {"kodeGejala": "G24", "namaGejala": "Jarang sakit"},
            {"kodeGejala": "G25", "namaGejala": "Perkembangan motorik normal"},
        ]
        
        # Create symptoms
        for gejala in gejala_data:
            Gejala.objects.create(**gejala)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {len(gejala_data)} symptoms'))
        
        # Define conditions (6 Kondisi)
        kondisi_data = [
            {
                "kodeKondisi": "K01",
                "namaKondisi": "Stunting",
                "deskripsi": "Gangguan pertumbuhan pada anak yang ditandai dengan tinggi badan lebih pendek dari anak seusianya. Stunting merupakan indikator status gizi kronis yang disebabkan oleh kurangnya asupan gizi dalam waktu lama serta terkena penyakit berulang.",
                "solusi": "1. Pastikan asupan gizi seimbang dengan protein, karbohidrat, lemak, vitamin, dan mineral\n2. Berikan ASI eksklusif hingga usia 6 bulan\n3. Lanjutkan pemberian ASI dan MPASI sampai usia 2 tahun\n4. Imunisasi lengkap sesuai jadwal\n5. Periksakan tumbuh kembang anak secara berkala ke posyandu atau fasilitas kesehatan"
            },
            {
                "kodeKondisi": "K02",
                "namaKondisi": "Gizi Buruk",
                "deskripsi": "Kondisi gizi ekstrem akibat kekurangan kalori dan protein secara berat, ditandai dengan berat badan sangat rendah, kemungkinan adanya edema, dan risiko kematian tinggi.",
                "solusi": "1. Segera bawa anak ke fasilitas kesehatan untuk penanganan medis intensif\n2. Program terapi gizi dengan susu khusus sesuai resep dokter\n3. Pantau berat badan dan kondisi klinis secara ketat\n4. Obati infeksi penyerta jika ada\n5. Edukasi orang tua tentang pemberian makanan bergizi"
            },
            {
                "kodeKondisi": "K03",
                "namaKondisi": "Risiko Stunting",
                "deskripsi": "Anak menunjukkan gejala awal yang mengarah pada stunting, seperti berat badan kurang, nafsu makan rendah, dan frekuensi makan rendah, namun belum mencapai kriteria stunting.",
                "solusi": "1. Tingkatkan frekuensi dan kualitas makanan\n2. Pastikan anak mendapat makanan bergizi 3 kali sehari ditambah 2 kali makanan selingan\n3. Periksakan tumbuh kembang anak secara berkala\n4. Edukasi orang tua tentang MPASI yang tepat\n5. Pantau pertumbuhan anak setiap bulan"
            },
            {
                "kodeKondisi": "K04",
                "namaKondisi": "Infeksi Berulang",
                "deskripsi": "Anak sering mengalami infeksi seperti demam, batuk, pilek, atau infeksi saluran pernapasan berulang yang dapat mengganggu proses penyerapan nutrisi.",
                "solusi": "1. Tingkatkan daya tahan tubuh dengan gizi seimbang\n2. Pastikan imunisasi lengkap\n3. Jaga kebersihan lingkungan dan diri anak\n4. Hindari paparan terhadap sumber infeksi\n5. Konsultasi ke dokter untuk pemeriksaan lebih lanjut"
            },
            {
                "kodeKondisi": "K05",
                "namaKondisi": "Pola Makan/Gangguan Makan",
                "deskripsi": "Anak mengalami gangguan dalam pola makan seperti tidak mau makan, muntah setelah makan, atau gangguan perilaku makan yang mengganggu asupan gizi.",
                "solusi": "1. Evaluasi pola makan anak bersama ahli gizi\n2. Terapkan teknik pemberian makan yang menyenangkan\n3. Perbaiki lingkungan makan yang kondusif\n4. Jika diperlukan, rujuk ke psikolog anak untuk gangguan perilaku makan\n5. Libatkan anak dalam persiapan makanan untuk meningkatkan minat makan"
            },
            {
                "kodeKondisi": "K06",
                "namaKondisi": "Normal/ Tidak Berisiko",
                "deskripsi": "Anak memiliki pertumbuhan dan perkembangan yang normal sesuai standar, dengan berat badan, tinggi badan, dan perkembangan motorik dalam rentang normal.",
                "solusi": "1. Pertahankan pola makan bergizi seimbang\n2. Terus berikan ASI dan MPASI yang tepat\n3. Lakukan stimulasi tumbuh kembang sesuai usia\n4. Imunisasi lengkap sesuai jadwal\n5. Periksakan tumbuh kembang secara rutin ke posyandu"
            }
        ]
        
        # Create conditions
        for kondisi in kondisi_data:
            Kondisi.objects.create(**kondisi)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {len(kondisi_data)} conditions'))
        
        # Define rules (Aturan) - linking conditions and symptoms
        aturan_data = [
            # K01 - Stunting (R01)
            {"kodeKelompokAturan": "R01", "kondisi_kode": "K01", "gejala_kode": "G01"},
            
            # K02 - Gizi Buruk (R02)
            {"kodeKelompokAturan": "R02", "kondisi_kode": "K02", "gejala_kode": "G02"},
            {"kodeKelompokAturan": "R02", "kondisi_kode": "K02", "gejala_kode": "G03"},
            {"kodeKelompokAturan": "R02", "kondisi_kode": "K02", "gejala_kode": "G07"},
            {"kodeKelompokAturan": "R02", "kondisi_kode": "K02", "gejala_kode": "G08"},
            {"kodeKelompokAturan": "R02", "kondisi_kode": "K02", "gejala_kode": "G14"},
            {"kodeKelompokAturan": "R02", "kondisi_kode": "K02", "gejala_kode": "G15"},
            
            # K03 - Risiko Stunting (R03)
            {"kodeKelompokAturan": "R03", "kondisi_kode": "K03", "gejala_kode": "G02"},
            {"kodeKelompokAturan": "R03", "kondisi_kode": "K03", "gejala_kode": "G03"},
            {"kodeKelompokAturan": "R03", "kondisi_kode": "K03", "gejala_kode": "G10"},
            {"kodeKelompokAturan": "R03", "kondisi_kode": "K03", "gejala_kode": "G11"},
            {"kodeKelompokAturan": "R03", "kondisi_kode": "K03", "gejala_kode": "G12"},
            {"kodeKelompokAturan": "R03", "kondisi_kode": "K03", "gejala_kode": "G15"},
            
            # K04 - Infeksi Berulang (R04)
            {"kodeKelompokAturan": "R04", "kondisi_kode": "K04", "gejala_kode": "G05"},
            {"kodeKelompokAturan": "R04", "kondisi_kode": "K04", "gejala_kode": "G09"},
            {"kodeKelompokAturan": "R04", "kondisi_kode": "K04", "gejala_kode": "G13"},
            
            # K05 - Pola Makan/Gangguan Makan (R05)
            {"kodeKelompokAturan": "R05", "kondisi_kode": "K05", "gejala_kode": "G04"},
            {"kodeKelompokAturan": "R05", "kondisi_kode": "K05", "gejala_kode": "G05"},
            {"kodeKelompokAturan": "R05", "kondisi_kode": "K05", "gejala_kode": "G06"},
            {"kodeKelompokAturan": "R05", "kondisi_kode": "K05", "gejala_kode": "G16"},
            {"kodeKelompokAturan": "R05", "kondisi_kode": "K05", "gejala_kode": "G17"},
            {"kodeKelompokAturan": "R05", "kondisi_kode": "K05", "gejala_kode": "G18"},
            {"kodeKelompokAturan": "R05", "kondisi_kode": "K05", "gejala_kode": "G19"},
            {"kodeKelompokAturan": "R05", "kondisi_kode": "K05", "gejala_kode": "G20"},
            
            # K06 - Normal/ Tidak Berisiko (R06)
            {"kodeKelompokAturan": "R06", "kondisi_kode": "K06", "gejala_kode": "G21"},
            {"kodeKelompokAturan": "R06", "kondisi_kode": "K06", "gejala_kode": "G22"},
            {"kodeKelompokAturan": "R06", "kondisi_kode": "K06", "gejala_kode": "G23"},
            {"kodeKelompokAturan": "R06", "kondisi_kode": "K06", "gejala_kode": "G24"},
            {"kodeKelompokAturan": "R06", "kondisi_kode": "K06", "gejala_kode": "G25"},
        ]
        
        # Create rules
        for aturan in aturan_data:
            kondisi = Kondisi.objects.get(kodeKondisi=aturan["kondisi_kode"])
            gejala = Gejala.objects.get(kodeGejala=aturan["gejala_kode"])
            Aturan.objects.create(
                kodeKelompokAturan=aturan["kodeKelompokAturan"],
                kondisi=kondisi,
                gejala=gejala
            )
        
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {len(aturan_data)} rules'))
        self.stdout.write(self.style.SUCCESS('Knowledge base data loaded successfully!'))
import arcpy, os, json, sys
from sipentautils import zonalayer
from datetime import datetime
import math
# ======================
# ENVIRONMENT SETTINGS
# ======================
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# ======================
# PATH CONFIGURATION
# ======================

appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

zl_path = zonalayer.isZonaLayerComply()
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
config_path = os.path.join(ws_dir, "config.json")

configs = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        configs = json.load(f)

dataset_path = configs["dataset_path"]
gdb_path = configs['gdb_path']

titik_zona_path = os.path.join(dataset_path, 'Titik_Zona')
titik_sampel_path = os.path.join(dataset_path, 'Titik_Sampel')
titik_sampel_individual_path = os.path.join(dataset_path, 'Titik_Sampel_Individual')

titik_pembanding_path = titik_sampel_path
if arcpy.Exists(titik_zona_path):
    titik_pembanding_path = titik_zona_path
    arcpy.AddMessage("Menggunakan dataset 'Titik_Zona' sebagai sumber pembanding.")

if not arcpy.Exists(titik_sampel_path):
    arcpy.AddError('Layer Titik Sampel tidak ditemukan')
    sys.exit(1)
elif not arcpy.Exists(titik_sampel_individual_path):
    arcpy.AddError('Layer Titik Sampel Individual tidak ditemukan')
    sys.exit(1)

# ======================
# USER INPUT
# ======================
nomor_entry_titik_sampel_individual = arcpy.GetParameterAsText(0)
nomor_entry_pembanding_satu = arcpy.GetParameterAsText(1)
nomor_entry_pembanding_dua = arcpy.GetParameterAsText(2)
nomor_entry_pembanding_ketiga = arcpy.GetParameterAsText(3)

# ======================
# VALIDASI DUPLIKASI INPUT
# ======================

inputs = {
    "Titik Individual": nomor_entry_titik_sampel_individual,
    "Pembanding 1": nomor_entry_pembanding_satu,
    "Pembanding 2": nomor_entry_pembanding_dua,
    "Pembanding 3": nomor_entry_pembanding_ketiga
}

# Cek apakah ada duplikasi antar semua input
nilai_set = set(inputs.values())

if len(nilai_set) < len(inputs):
    # Jika jumlah unik lebih sedikit dari total input, berarti ada duplikasi
    duplikat = [key for key, value in inputs.items() if list(inputs.values()).count(value) > 1]
    arcpy.AddError(f"Ada duplikasi input antara: {', '.join(set(duplikat))}. Pastikan semua titik berbeda.")
    sys.exit(1)

# Cek khusus: nomor_entry_titik_sampel_individual tidak boleh menjadi salah satu pembanding
if nomor_entry_titik_sampel_individual in [nomor_entry_pembanding_satu, nomor_entry_pembanding_dua, nomor_entry_pembanding_ketiga]:
    arcpy.AddError("Titik individual yang akan dinilai tidak boleh sama dengan salah satu pembanding.")
    sys.exit(1)


# ======================
# VALIDASI KESEDIAAN DATA
# ======================

# 1️⃣ Ambil semua Nomor_Entry dari layer Titik_Sampel_Individual
nomor_entry_individual = set()
with arcpy.da.SearchCursor(titik_sampel_individual_path, ["Nomor_Entry"]) as cursor:
    for row in cursor:
        nomor_entry_individual.add(str(row[0]))

# 2️⃣ Ambil semua Nomor_Entry dari layer pembanding
nomor_entry_sampel = set()
with arcpy.da.SearchCursor(titik_pembanding_path, ["Nomor_Entry"]) as cursor:
    for row in cursor:
        nomor_entry_sampel.add(str(row[0]))

# 3️⃣ Cek apakah nomor_entry_titik_sampel_individual ada di layer Titik_Sampel_Individual
if nomor_entry_titik_sampel_individual not in nomor_entry_individual:
    arcpy.AddError(f"Titik individual '{nomor_entry_titik_sampel_individual}' tidak ditemukan di layer Titik_Sampel_Individual.")
    sys.exit(1)

# 4️⃣ Cek apakah pembanding-pembanding ada di layer pembanding
for idx, pembanding in enumerate([nomor_entry_pembanding_satu, nomor_entry_pembanding_dua, nomor_entry_pembanding_ketiga], start=1):
    if pembanding not in nomor_entry_sampel:
        arcpy.AddError(f"Pembanding {idx} ('{pembanding}') tidak ditemukan di layer Titik_Sampel.")
        sys.exit(1)

arcpy.AddMessage("✅ Semua input valid. Titik individual dan pembanding ditemukan di layer masing-masing.")


# ======================
# FUNGSI PENYESUAIAN DATA PEMBANDING
# ======================

def penyesuaian_harga_tanah_m2(harga_penawaran_atau_transaksi, nilai_bangunan, luas_tanah, tipe_transaksi):

    # penyesuaian harga penawaran atau transaksi: jika penawaran nilainya 90% jika transaksi 100%
    penyesuaian_harga_penawaran_atau_transaksi = 0.9 * harga_penawaran_atau_transaksi if tipe_transaksi == 'Penawaran' else harga_penawaran_atau_transaksi
    
    # nilai tanah kosong
    harga_tanah_kosong = penyesuaian_harga_penawaran_atau_transaksi - nilai_bangunan

    # mendapatkan harga tanah per m2
    harga_tanah_per_m2 = harga_tanah_kosong / luas_tanah

    return harga_tanah_per_m2

def penyesuaian_waktu_transaksi(waktu_transaksi_penjualan, persentase=0.10):
    """
    Menghitung penyesuaian waktu terhadap harga transaksi berdasarkan selisih tahun
    antara tanggal transaksi dan tanggal hari ini.

    Parameter:
    ----------
    waktu_transaksi_penjualan : str | datetime
        Tanggal transaksi penjualan dalam format 'YYYY-MM-DD' atau objek datetime.
    persentase : float
        Persentase penyusutan per tahun (contoh: 0.1 berarti 10% per tahun). Maih harus dipastikan apakah persentase itu konstanta atau sesuai konfig pengguna
    """
    
    # Pastikan waktu_transaksi_penjualan dalam bentuk datetime
    if isinstance(waktu_transaksi_penjualan, str):
        try:
            waktu_transaksi_penjualan = datetime.strptime(waktu_transaksi_penjualan, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Format tanggal tidak valid. Gunakan format 'YYYY-MM-DD'.")

    # Hitung selisih waktu (dalam tahun desimal)
    waktu_sekarang = datetime.today()
    selisih_hari = (waktu_sekarang - waktu_transaksi_penjualan).days
    selisih_tahun = selisih_hari / 365.0  # Konversi ke tahun

    return  persentase * selisih_tahun

def penyesuaian_hak(jenis_hak_individual, jenis_hak_pembanding, persentase = 0.04):

    bobot_hak = {
        'TMA': 1,
        'HGB': 2,
        'HP': 2,
        'HGU': 2,
        'HM': 3
    }

    persentase_penyesuaian = (bobot_hak[jenis_hak_individual] - bobot_hak[jenis_hak_pembanding]) * persentase

    return persentase_penyesuaian

def penyesuaian_luas_tanah(luas_tanah_individu, luas_tanah_pembanding, persentase=0.005):
    bobot_luas_tanah = [
        {'batas_atas': 50, 'bobot': 1},
        {'batas_atas': 80, 'bobot': 2},
        {'batas_atas': 120, 'bobot': 3},
        {'batas_atas': 200, 'bobot': 4},
    ]

    def hitung_bobot(luas):
        for kelas in bobot_luas_tanah:
            if luas <= kelas['batas_atas']:
                return kelas['bobot']
        return 1

    bobot_individu = hitung_bobot(luas_tanah_individu)
    bobot_pembanding = hitung_bobot(luas_tanah_pembanding)

    persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
    return persentase_penyesuaian

def penyesuaian_lebar_depan(lebar_depan_individu, lebar_depan_pembanding, persentase=0.015):
    bobot_lebar_depan = [
        {'batas_atas': 6, 'bobot': 1},
        {'batas_atas': 12, 'bobot': 2},
        {'batas_atas': 15, 'bobot': 3}
    ]

    def hitung_bobot(lebar):
        for kelas in bobot_lebar_depan:
            if lebar <= kelas['batas_atas']:
                return kelas['bobot']
        return bobot_lebar_depan[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

    bobot_individu = hitung_bobot(lebar_depan_individu)
    bobot_pembanding = hitung_bobot(lebar_depan_pembanding)

    persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
    return persentase_penyesuaian

def penyesuaian_bentuk_tanah(bentuk_tanah_individu, bentuk_tanah_pembanding, persentase=0.015):
    
    bobot_bentuk_tanah = [
        {'deskripsi': 'Tidak Beraturan', 'bobot': 1},
        {'deskripsi': 'Persegi Panjang/Trapesium', 'bobot': 2},
        {'deskripsi': 'Persegi/Normal', 'bobot': 3}
    ]

    def hitung_bobot(bentuk_tanah):
        for kelas in bobot_bentuk_tanah:
            if bentuk_tanah == kelas['deskripsi']:
                return kelas['bobot']
            
        arcpy.AddError('Data bentuk tanah pada pembanding tidak bisa dibaca')
        sys.exit(1)

        return bobot_bentuk_tanah[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

    bobot_individu = hitung_bobot(bentuk_tanah_individu)
    bobot_pembanding = hitung_bobot(bentuk_tanah_pembanding)

    persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
    return persentase_penyesuaian

def penyesuaian_elevasi_tanah(elevasi_tanah_individu, elevasi_tanah_pembanding, persentase=0.025):
    
    bobot_elevasi_tanah = [
        {'deskripsi': 'Lebih Rendah', 'bobot': 1},
        {'deskripsi': 'Sama', 'bobot': 2},
        {'deskripsi': 'Lebih Tinggi', 'bobot': 3}
    ]

    def hitung_bobot(elevasi_tanah):
        for kelas in bobot_elevasi_tanah:
            if elevasi_tanah == kelas['deskripsi']:
                return kelas['bobot']
            
        arcpy.AddError('Data elevasi tanah pada pembanding tidak bisa dibaca')
        sys.exit(1)

        return bobot_elevasi_tanah[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

    bobot_individu = hitung_bobot(elevasi_tanah_individu)
    bobot_pembanding = hitung_bobot(elevasi_tanah_pembanding)

    persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
    return persentase_penyesuaian

def penyesuaian_letak_tanah(letak_tanah_individu, letak_tanah_pembanding, persentase=0.01):

    bobot_letak_tanah = [
        {'deskripsi': 'Lain-Lain', 'bobot': 1},
        {'deskripsi': 'Tusuk Sate', 'bobot': 2},
        {'deskripsi': 'Normal', 'bobot': 3},
        {'deskripsi': 'Hadap Taman', 'bobot': 4},
        {'deskripsi': 'Huk', 'bobot': 5}
    ]

    def hitung_bobot(letak_tanah):
        for kelas in bobot_letak_tanah:
            if letak_tanah == kelas['deskripsi']:
                return kelas['bobot']
            
        arcpy.AddError('Data letak tanah pada pembanding tidak bisa dibaca')
        sys.exit(1)

        return bobot_letak_tanah[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

    bobot_individu = hitung_bobot(letak_tanah_individu)
    bobot_pembanding = hitung_bobot(letak_tanah_pembanding)

    persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
    return persentase_penyesuaian

def penyesuaian_kelas_jalan(kelas_jalan_individu, kelas_jalan_pembanding, persentase=0.05):
			

    bobot_kelas_jalan = [
        {'deskripsi': 'Setapak', 'bobot': 1},
        {'deskripsi': 'Lokal', 'bobot': 2},
        {'deskripsi': 'Kolektor', 'bobot': 3},
        {'deskripsi': 'Arteri', 'bobot': 4}
    ]

    def hitung_bobot(kelas_jalan):
        for kelas in bobot_kelas_jalan:
            if kelas_jalan == kelas['deskripsi']:
                return kelas['bobot']
            
        arcpy.AddError('Data kelas jalan pada pembanding tidak bisa dibaca')
        sys.exit(1)

        return bobot_kelas_jalan[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

    bobot_individu = hitung_bobot(kelas_jalan_individu)
    bobot_pembanding = hitung_bobot(kelas_jalan_pembanding)

    persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
    return persentase_penyesuaian

def penyesuaian_drainase(drainase_individu, drainase_pembanding, persentase=0.05):
			
    bobot_drainase = [
        {'deskripsi': 'kurang', 'bobot': 1},
        {'deskripsi': 'cukup', 'bobot': 2},
        {'deskripsi': 'baik', 'bobot': 3},
        {'deskripsi': 'sangat baik', 'bobot': 4}
    ]

    def hitung_bobot(drainase):
        for kelas in bobot_drainase:
            if drainase == kelas['deskripsi']:
                return kelas['bobot']
            
        arcpy.AddError(f'Data drainase pada pembanding {drainase} tidak bisa dibaca')
        sys.exit(1)

        return bobot_drainase[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

    bobot_individu = hitung_bobot(drainase_individu)
    bobot_pembanding = hitung_bobot(drainase_pembanding)

    persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
    return persentase_penyesuaian

def penyesuaian_aksesibilitas(aksesibilitas_individu, aksesibilitas_pembanding, persentase=0.02):
			
    bobot_aksesibilitas = [
        {'deskripsi': 'kurang', 'bobot': 1},
        {'deskripsi': 'cukup', 'bobot': 2},
        {'deskripsi': 'baik', 'bobot': 3},
        {'deskripsi': 'sangat baik', 'bobot': 4}
    ]

    def hitung_bobot(aksesibilitas):
        for kelas in bobot_aksesibilitas:
            if aksesibilitas == kelas['deskripsi']:
                return kelas['bobot']
            
        arcpy.AddError('Data aksesibilitas pada pembanding tidak bisa dibaca')
        sys.exit(1)

        return bobot_aksesibilitas[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

    bobot_individu = hitung_bobot(aksesibilitas_individu)
    bobot_pembanding = hitung_bobot(aksesibilitas_pembanding)

    persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
    return persentase_penyesuaian

def penyesuaian_fasum(fasum_individu, fasum_pembanding, persentase=0.02):

    total_fasum_individu = len([item.strip() for item in fasum_individu.split(',') if item.strip()])

    # Jika tidak ada fasum → bobot 1
    # Jika lebih dari 4 → bobot 4
    # Selain itu → bobot sesuai jumlah fasum
    if total_fasum_individu < 1:
        bobot_individu = 1
    elif total_fasum_individu > 4:
        bobot_individu = 4
    else:
        bobot_individu = total_fasum_individu
    
    total_fasum_pembanding = len([item.strip() for item in fasum_pembanding.split(',') if item.strip()])

    # Jika tidak ada fasum → bobot 1
    # Jika lebih dari 4 → bobot 4
    # Selain itu → bobot sesuai jumlah fasum
    if total_fasum_pembanding < 1:
        bobot_pembanding = 1
    elif total_fasum_pembanding > 4:
        bobot_pembanding = 4
    else:
        bobot_pembanding = total_fasum_pembanding
 

    persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
    return persentase_penyesuaian

def penyesuaian_utilitas(utilitas_individu, utilitas_pembanding, persentase=0.01):

    total_utilitas_individu = len([item.strip() for item in utilitas_individu.split(',') if item.strip()])

    # Jika tidak ada utilitas → bobot 1
    # Jika lebih dari 4 → bobot 4
    # Selain itu → bobot sesuai jumlah utilitas
    if total_utilitas_individu < 1:
        bobot_individu = 1
    elif total_utilitas_individu > 4:
        bobot_individu = 4
    else:
        bobot_individu = total_utilitas_individu
    
    total_utilitas_pembanding = len([item.strip() for item in utilitas_pembanding.split(',') if item.strip()])

    # Jika tidak ada utilitas → bobot 1
    # Jika lebih dari 4 → bobot 4
    # Selain itu → bobot sesuai jumlah utilitas
    if total_utilitas_pembanding < 1:
        bobot_pembanding = 1
    elif total_utilitas_pembanding > 4:
        bobot_pembanding = 4
    else:
        bobot_pembanding = total_utilitas_pembanding
 

    persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
    return persentase_penyesuaian

def penyesuaian_kelas_lokasi(kelas_lokasi_individu, kelas_lokasi_pembanding, persentase=0.05):
			

    bobot_kelas_lokasi = [
        {'deskripsi': 'Setapak', 'bobot': 1},
        {'deskripsi': 'Lokal', 'bobot': 2},
        {'deskripsi': 'Kolektor', 'bobot': 3},
        {'deskripsi': 'Arteri', 'bobot': 4}
    ]

    def hitung_bobot(kelas_lokasi):
        for kelas in bobot_kelas_lokasi:
            if kelas_lokasi == kelas['deskripsi']:
                return kelas['bobot']
            
        arcpy.AddError('Data kelas jalan pada pembanding tidak bisa dibaca')
        sys.exit(1)

        return bobot_kelas_lokasi[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

    bobot_individu = hitung_bobot(kelas_lokasi_individu)
    bobot_pembanding = hitung_bobot(kelas_lokasi_pembanding)

    persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
    return persentase_penyesuaian

# ======================
# MAIN PROCESSING
# ======================

def dapatkan_data_sampel(nomor_entry, layer_sumber):
    # Struktur data awal
    data_format = {
        'id': 0,
        'alamat': '',
        'luas_bangunan': 0,
        'waktu_transaksi_penjualan': None,
        'status_hak': '',
        'fisik_tanah': {
            'luas_tanah': 0,
            'lebar_depan': 0,
            'bentuk_tanah': '',
            'elevasi_tanah': '',
            'letak_tanah': '',
            'kelas_jalan': ''
        },
        'drainase': '',
        'aksesibilitas': '',
        'fasum': '',
        'utilitas': '',
        'kelas_lokasi': '',
        'jenis_data': '',
        'harga_penawaran_atau_transaksi': 0,
        'nilai_bangunan': 0,
        'penyesuaian_waktu': 0,
        'penyesuaian_kepemilikan': 0,
    }

    # Daftar field yang ingin diambil dari attribute table
    field_list = [
        'Nomor_Entry', 'Alamat', 'Luas_Bangunan', 'Tgl_Penawaran_Transaksi',
        'Status_Kepemilikan', 'Luas_Tanah_m2', 'Lebar_Depan', 'Bentuk_Tanah',
        'Elevasi_Dari_Jalan', 'Letak_Tanah', 'Kelas_Jalan', 'Drainase',
        'Aksebilitas', 'Fasilitas', 'Utilitas', 'akses',
        'Jenis_Data', 'Harga_Penawaran_Transaksi', 'Nilai_Bangunan',
        'Penyesuaian_Waktu', 'Penyesuaian_Status_Kepemilikan'
    ]

    # Buka cursor untuk membaca data dari layer
    with arcpy.da.SearchCursor(layer_sumber, field_list, f"Nomor_Entry = {nomor_entry}") as cursor:
        for row in cursor:
            data_format['id'] = row[0]
            data_format['alamat'] = row[1]
            data_format['luas_bangunan'] = row[2]
            data_format['waktu_transaksi_penjualan'] = datetime.strptime(row[3], "%Y-%m-%d")
            data_format['status_hak'] = row[4]

            # Masukkan data fisik tanah ke sub-dictionary
            data_format['fisik_tanah']['luas_tanah'] = row[5]
            data_format['fisik_tanah']['lebar_depan'] = row[6]
            data_format['fisik_tanah']['bentuk_tanah'] = row[7]
            data_format['fisik_tanah']['elevasi_tanah'] = row[8]
            data_format['fisik_tanah']['letak_tanah'] = row[9]
            data_format['fisik_tanah']['kelas_jalan'] = row[10]

            # Sisanya langsung diisi
            data_format['drainase'] = row[11].lower()
            data_format['aksesibilitas'] = row[12].lower()
            data_format['fasum'] = row[13]
            data_format['utilitas'] = row[14]
            data_format['kelas_lokasi'] = row[15]
            data_format['jenis_data'] = row[16]
            data_format['harga_penawaran_atau_transaksi'] = row[17]
            data_format['nilai_bangunan'] = row[18]
            data_format['penyesuaian_waktu'] = row[19]
            data_format['penyesuaian_kepemilikan'] = row[20]

            break  # Hanya ambil satu baris (nomor_entry unik)

    return data_format

def ambil_dan_hitung_kesesuaian(data_individual, nomor_entry, layer_path):
    """Ambil data sampel dan hitung harga per m2"""
    data = dapatkan_data_sampel(nomor_entry, layer_path)

    harga_per_m2 = penyesuaian_harga_tanah_m2(
        data['harga_penawaran_atau_transaksi'],
        data['nilai_bangunan'],
        data['fisik_tanah']['luas_tanah'],
        data['jenis_data']
    )

    # Pastikan key 'perhitungan' sudah ada
    if 'perhitungan' not in data:
        data['perhitungan'] = {}

    data['perhitungan']['penyesuaian_harga_tanah_m2'] = harga_per_m2

    penyusutan_waktu = penyesuaian_waktu_transaksi(data['waktu_transaksi_penjualan'])

    data['perhitungan']['penyusutan_waktu'] = penyusutan_waktu

    persentase_penyesuaian_hak = penyesuaian_hak(data_individual['status_hak'], data['status_hak'],)

    data['perhitungan']['penyusutan_hak'] = persentase_penyesuaian_hak

    persentase_penyesuaian_luas_tanah = penyesuaian_luas_tanah(data_individual['fisik_tanah']['luas_tanah'], data['fisik_tanah']['luas_tanah'],)

    data['perhitungan']['penyesuaian_luas_tanah'] = persentase_penyesuaian_luas_tanah

    persentase_penyesuaian_lebar_depan = penyesuaian_lebar_depan(data_individual['fisik_tanah']['lebar_depan'], data['fisik_tanah']['lebar_depan'],)

    data['perhitungan']['penyesuaian_lebar_depan'] = persentase_penyesuaian_lebar_depan

    persentase_penyesuaian_bentuk_tanah = penyesuaian_bentuk_tanah(data_individual['fisik_tanah']['bentuk_tanah'], data['fisik_tanah']['bentuk_tanah'],)

    data['perhitungan']['penyesuaian_bentuk_tanah'] = persentase_penyesuaian_bentuk_tanah

    persentase_penyesuaian_elevasi_tanah = penyesuaian_elevasi_tanah(data_individual['fisik_tanah']['elevasi_tanah'], data['fisik_tanah']['elevasi_tanah'],)

    data['perhitungan']['penyesuaian_elevasi_tanah'] = persentase_penyesuaian_elevasi_tanah

    persentase_penyesuaian_letak_tanah = penyesuaian_letak_tanah(data_individual['fisik_tanah']['letak_tanah'], data['fisik_tanah']['letak_tanah'],)

    data['perhitungan']['penyesuaian_letak_tanah'] = persentase_penyesuaian_letak_tanah

    persentase_penyesuaian_kelas_jalan = penyesuaian_kelas_jalan(data_individual['fisik_tanah']['kelas_jalan'], data['fisik_tanah']['kelas_jalan'],)

    data['perhitungan']['penyesuaian_kelas_jalan'] = persentase_penyesuaian_kelas_jalan

    persentase_penyesuaian_drainase = penyesuaian_drainase(data_individual['drainase'], data['drainase'],)

    data['perhitungan']['penyesuaian_drainase'] = persentase_penyesuaian_drainase

    persentase_penyesuaian_aksesibilitas = penyesuaian_aksesibilitas(data_individual['aksesibilitas'], data['aksesibilitas'],)

    data['perhitungan']['penyesuaian_aksesibilitas'] = persentase_penyesuaian_aksesibilitas

    persentase_penyesuaian_fasum = penyesuaian_fasum(data_individual['fasum'], data['fasum'],)

    data['perhitungan']['penyesuaian_fasum'] = persentase_penyesuaian_fasum

    persentase_penyesuaian_utilitas = penyesuaian_utilitas(data_individual['utilitas'], data['utilitas'],)

    data['perhitungan']['penyesuaian_utilitas'] = persentase_penyesuaian_utilitas

    persentase_penyesuaian_kelas_lokasi = penyesuaian_kelas_lokasi(data_individual['kelas_lokasi'], data['kelas_lokasi'],)

    data['perhitungan']['penyesuaian_kelas_lokasi'] = persentase_penyesuaian_kelas_lokasi

    total_penyesuaian = sum(
    v for k, v in data['perhitungan'].items() 
    if isinstance(v, (int, float)) and abs(v) < 1000  # abaikan nilai besar seperti harga_per_m2
    )
    data['total_penyesuaian'] = total_penyesuaian

    indikasi_nilai = data['perhitungan']['penyesuaian_harga_tanah_m2'] * ( 1 + total_penyesuaian)
    data['indikasi_nilai'] = indikasi_nilai


    absolut_values = {k: abs(v * 100) for k, v in data['perhitungan'].items() if k != 'penyesuaian_harga_tanah_m2'}
    jumlah_nol_absolut = sum(1 for v in absolut_values.values() if v == 0)

    data['total_absolute_nol'] = jumlah_nol_absolut
    return data


# ===========================
# PEMANGGILAN UTAMA
# ===========================
data_individual = data = dapatkan_data_sampel(nomor_entry_titik_sampel_individual, titik_sampel_individual_path)
data_pembanding_pertama = ambil_dan_hitung_kesesuaian(data_individual, nomor_entry_pembanding_satu, titik_pembanding_path)
data_pembanding_kedua = ambil_dan_hitung_kesesuaian(data_individual, nomor_entry_pembanding_dua, titik_pembanding_path)
data_pembanding_ketiga = ambil_dan_hitung_kesesuaian(data_individual, nomor_entry_pembanding_ketiga, titik_pembanding_path)

jumlah_keseluruhan_nol_absolut = data_pembanding_pertama['total_absolute_nol'] + data_pembanding_kedua['total_absolute_nol'] + data_pembanding_ketiga['total_absolute_nol']

data_pembanding_pertama['rekonsiliasi_atau_pembobotan'] = data_pembanding_pertama['total_absolute_nol'] / jumlah_keseluruhan_nol_absolut 
data_pembanding_kedua['rekonsiliasi_atau_pembobotan'] = data_pembanding_kedua['total_absolute_nol'] / jumlah_keseluruhan_nol_absolut
data_pembanding_ketiga['rekonsiliasi_atau_pembobotan'] = data_pembanding_ketiga['total_absolute_nol'] / jumlah_keseluruhan_nol_absolut

data_pembanding_pertama['nilai_setelah_pembobotan'] = data_pembanding_pertama['indikasi_nilai'] * data_pembanding_pertama['rekonsiliasi_atau_pembobotan']
data_pembanding_kedua['nilai_setelah_pembobotan'] = data_pembanding_kedua['indikasi_nilai'] * data_pembanding_kedua['rekonsiliasi_atau_pembobotan']
data_pembanding_ketiga['nilai_setelah_pembobotan'] = data_pembanding_ketiga['indikasi_nilai'] * data_pembanding_ketiga['rekonsiliasi_atau_pembobotan']


nilai_pasar_data_individual = data_pembanding_pertama['nilai_setelah_pembobotan'] + data_pembanding_kedua['nilai_setelah_pembobotan'] + data_pembanding_ketiga['nilai_setelah_pembobotan']
data_individual['nilai_pasar_per_m2'] = nilai_pasar_data_individual

nilai_pasar_per_m2 = round(math.ceil(data_individual['nilai_pasar_per_m2'] * data_individual['fisik_tanah']['luas_tanah']) / 1_000) * 1_000

arcpy.AddMessage(math.ceil(data_individual['nilai_pasar_per_m2'] * data_individual['fisik_tanah']['luas_tanah']))
data_individual['nilai_pasar'] = nilai_pasar_per_m2




fields_to_update = ["Nomor_Entry", 
                    "Harga_Penawaran_Transaksi", 
                    "Harga_Penyesuaian",
                    "Harga_Tanah_Rp",
                    "nilluas",
                    "nilai",
                    "Pembanding"]  # ganti dengan kolom yang ingin diupdate

pembanding = f"{data_pembanding_pertama['id']},{data_pembanding_kedua['id']},{data_pembanding_ketiga['id']}"
harga_tanah = data_individual['nilai_pasar'] - data_individual['nilai_bangunan']
data_individual['harga_tanah'] = harga_tanah
data_individual['harga_tanah_Rp'] = f"Rp {harga_tanah:,.0f}".replace(",", ".")

data_individual['nilai_luas'] = (1 + (data_individual['penyesuaian_waktu'] /100)+ (data_individual['penyesuaian_kepemilikan'] /100)) * data_individual['harga_tanah']
data_individual['nilai'] = data_individual['nilai_luas'] / data_individual['fisik_tanah']['luas_tanah']

with arcpy.da.UpdateCursor(titik_sampel_individual_path, fields_to_update) as cursor:
    for row in cursor:
        nomor_entry = int(row[0])

        if nomor_entry == data_individual['id']:
            row[1] = data_individual['nilai_pasar']
            row[2] = data_individual['nilai_pasar']
            row[3] = data_individual['harga_tanah_Rp']
            row[4] = data_individual['nilai_luas']
            row[5] = data_individual['nilai']
            row[6] = pembanding

            cursor.updateRow(row)

ui_folder = os.path.join(appdata, "ui")
symbology_folder = os.path.join(ui_folder, "symbology")
tsi_simbology_path = os.path.join(symbology_folder, "Titik_Sampel_Individual.lyrx")


arcpy.management.MakeFeatureLayer(titik_sampel_individual_path, "Titik_Sampel_Individual")
arcpy.management.ApplySymbologyFromLayer("Titik_Sampel_Individual", tsi_simbology_path)

arcpy.SetParameter(4, "Titik_Sampel_Individual")







# ======================
# ENVIRONMENT SETTINGS
# ======================
import arcpy, os, json
from sipentautils import zonalayer, samplepoint

# Mengatur environment agar output bisa di-overwrite jika file sudah ada
arcpy.env.overwriteOutput = True
# ======================
# PATH CONFIGURATION
# ======================

# Konfigurasi Path Aplikasi
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


# Konfigurasi Path Project
zl_path = zonalayer.isZonaLayerComply()
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
config_path = os.path.join(ws_dir, "config.json")
configs = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        configs = json.load(f)

gdb_path = configs['gdb_path']
dataset_path = configs['dataset_path']

# Nama layer peta yang digunakan
# Titik_Zona: Layer sumber data zona dengan informasi quartile

titik_zona = "Titik_Zona"
titik_sampel = "Titik_Sampel"
titik_zona_path = os.path.join(dataset_path, titik_zona)
titik_sampel_path = os.path.join(dataset_path, titik_sampel)

# Fungsi ini menghitung Q1 (quartile 1), Q2 (median), dan Q3 (quartile 3) dari sekumpulan nilai
def quartiles(values):
    values = sorted(values)  # Urutkan nilai secara ascending
    size = len(values)
    
    # Jika jumlah data kurang dari 4, tidak bisa menghitung quartile yang valid
    if size < 4:
        return None
    
    mid = size // 2  # Posisi tengah
    
    # Hitung Q2 (median)
    if size % 2 == 0:
        Q2 = (values[mid - 1] + values[mid]) / 2  # Rata-rata dua nilai tengah untuk data genap
    else:
        Q2 = values[mid]  # Nilai tengah langsung untuk data ganjil
    
    # Hitung Q1 (quartile bawah - median dari separuh data pertama)
    if mid % 2 == 0:
        Q1 = (values[mid // 2 - 1] + values[mid // 2]) / 2
    else:
        Q1 = values[mid // 2]
    
    # Hitung Q3 (quartile atas - median dari separuh data kedua)
    if (size - mid) % 2 == 0:
        Q3 = (values[(mid + size) // 2 - 1] + values[(mid + size) // 2]) / 2
    else:
        Q3 = values[(mid + size) // 2]
    
    return Q1, Q2, Q3


# ======================
# IDENTIFIKASI ZONA
# ======================

# Mengidentifikasi kombinasi zona unik berdasarkan field JNSZN
zones_type = set()  # Menggunakan set untuk mendapatkan nilai unik
with arcpy.da.SearchCursor(titik_zona_path, ["JNSZN"]) as cursor:
    for i, row in enumerate(cursor):
        if len(row) > 0:
            zones_type.add(row[0])
        else:
            arcpy.AddMessage("Baris kosong terdeteksi")
arcpy.AddMessage(f"Mengidentifikasi jenis zona unik berdasarkan field JNSZN...{zones_type}")

# ======================
# PROCESS KUARTIL
# ======================

# Proses setiap jenis zona secara terpisah
for jenis_zona in zones_type:
    # Buat query untuk memfilter data berdasarkan zona
    where = f"JNSZN = {jenis_zona}"

    # Ambil semua nilai indeks_sampel untuk zona ini
    values = [r[0] for r in arcpy.da.SearchCursor(titik_zona_path, ["indeks_sampel"], where_clause=where)]
    # jika pada jenis zona kurang dari 4 data  maka di skip (tidak cukup untuk analisis quartile)
    if len(values) < 4:
        arcpy.AddMessage(f"Jenis zona {jenis_zona} dilewati: hanya terdapat ({len(values)} data, kurang dari minimal 4)")
        continue

    # Hitung nilai quartile untuk zona ini
    Q1, Q2, Q3 = quartiles(values)
    arcpy.AddMessage(f"Jenis Zona ({jenis_zona}) : Q1={Q1:.2f}, Q2={Q2:.2f}, Q3={Q3:.2f}")
    jangkauan_kuartil = Q3-Q1

    batas_bawah = Q1 - (1.5*jangkauan_kuartil)
    batas_atas = Q3 + (1.5*jangkauan_kuartil)
    arcpy.AddMessage(f"Jenis Zona ({jenis_zona}) : Batas Bawah={batas_bawah:.2f}, Batas Atas={batas_atas:.2f}")

    

    # Buat query untuk mengidentifikasi outlier: nilai di bawah Q1 atau di atas Q3
    outlier_query = f"JNSZN = {jenis_zona} AND (indeks_sampel < {batas_bawah} OR indeks_sampel > {batas_atas})"

    # Buat feature layer sementara berisi data outlier
    sel_layer = arcpy.management.MakeFeatureLayer(titik_zona, "temp_quartile", outlier_query)[0]
    
    # Copy data outlier ke in_memory workspace untuk processing
    temp_copy = arcpy.management.CopyFeatures(sel_layer, "in_memory\\temp_copy_quartile")[0]

    # Dapatkan field yang common antara source dan target
    common_fields = samplepoint.get_common_fields(temp_copy, titik_sampel_path)
    insert_fields = common_fields + ["SHAPE@"]  # Tambahkan geometry field

    # Transfer data outlier dari Titik_Zona ke titik_sampel
    with arcpy.da.InsertCursor(titik_sampel_path, insert_fields) as icur:
        with arcpy.da.SearchCursor(temp_copy, insert_fields) as scur:
            for row in scur:
                icur.insertRow(row)  # Insert setiap baris outlier ke titik_sampel

    # Hapus data outlier dari Titik_Zona (karena sudah dipindahkan ke titik_sampel)
    arcpy.management.DeleteFeatures(sel_layer)
    
    # Cleanup: hapus temporary layer
    arcpy.management.Delete("in_memory\\temp_copy_quartile")
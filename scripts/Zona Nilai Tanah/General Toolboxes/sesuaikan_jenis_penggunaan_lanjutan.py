import os, arcpy, json
from sipentautils import zonalayer

# ======================
# ENVIRONMENT SETTINGS
# ======================
arcpy.env.outputZFlag = "Disabled"  # Menonaktifkan output nilai Z (3D)
arcpy.env.outputMFlag = "Disabled"  # Menonaktifkan output nilai M (measure)

# ======================
# PATH CONFIGURATION
# ======================

# Konfigurasi Path Aplikasi
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Konfigurasi Path Project
zl_path = zonalayer.isZonaLayerComply()  # Memeriksa dan mendapatkan path Zona Layer
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))  # Mendapatkan direktori workspace
config_path = os.path.join(ws_dir, "config.json")  # Path file konfigurasi
configs = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        configs = json.load(f)  # Memuat konfigurasi dari file JSON

# Mengambil nilai konfigurasi dari file config
dataset_path = configs["dataset_path"]  # Path dataset utama
THNNILAI = configs['THNNILAI']  # Tahun nilai
WADMKK = configs['WADMKK']  # Kode wilayah administrasi kabupaten/kota
WADMPR = configs['WADMPR']  # Kode wilayah administrasi provinsi
coor = configs['coord']  # Sistem koordinat
gdb_path = configs['gdb_path']  # Path geodatabase

# Mendefinisikan path dan variabel untuk data processing
zl = "Zona_Layer"  # Nama layer zona
sampel = os.path.join(dataset_path, "Titik_Sampel")  # Path layer titik sampel
out_temp = os.path.join(dataset_path, "Titik_Sampel_temp")  # Path output temporary
jenis = arcpy.GetParameterAsText(0)  # Mendapatkan parameter input jenis zona

# Mapping jenis zona ke kode numerik
JNSZN = 1  # Default value untuk Non-Pertanian
if jenis == "Non-Pertanian":
    JNSZN = 1
elif jenis == "Pertanian":
    JNSZN = 2
    
# ======================
# FIELD VALIDATION
# ======================

# Daftar field yang wajib ada
required_fields = ["JNSZN", "JENISSAMPEL", "PENGGUNAAN"]

# Dapatkan daftar field yang ada di layer
field_names = [field.name for field in arcpy.ListFields(zl)]

# Validasi field yang dibutuhkan
missing_fields = [field for field in required_fields if field not in field_names]

if missing_fields:
    # Jika ada field yang tidak ditemukan
    error_message = "ERROR: Field berikut dibutuhkan tetapi tidak ditemukan: " + ", ".join(missing_fields)
    arcpy.AddError(error_message)
    raise ValueError(error_message)

# ======================
# MAIN PROCESSING
# ======================

a = 1
ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(zl).FIDSet)  # Memeriksa apakah ada fitur yang dipilih

"""
Tahap 1: Update nilai field di Zona Layer untuk fitur yang dipilih
- Jika ada seleksi fitur, update field JNSZN, JENISSAMPEL, dan PENGGUNAAN
- JNSZN: Kode numerik jenis zona (1 untuk Non-Pertanian, 2 untuk Pertanian)
- JENISSAMPEL: Kode numerik yang sama dengan JNSZN
- PENGGUNAAN: Nama tekstual jenis zona
"""
if ada_seleksi > 0:
    # Update field-field di Zona Layer untuk fitur yang dipilih
    rows = arcpy.UpdateCursor(zl)
    for row in rows:
        row.setValue("JNSZN", JNSZN)  # Mengatur nilai JNSZN
        row.setValue("JENISSAMPEL", JNSZN)  # Mengatur nilai JENISSAMPEL
        row.setValue("PENGGUNAAN", jenis)  # Mengatur nilai PENGGUNAAN
        rows.updateRow(row)
    del row
    del rows

    """
    Tahap 2: Update field BEDA_ZONA berdasarkan perbandingan JNSZN dan JENISSAMPEL
    - Memeriksa kesesuaian antara nilai JNSZN dan nilai dalam JENISSAMPEL
    - JENISSAMPEL berisi daftar nilai yang dipisahkan koma
    - Jika JNSZN ada dalam daftar JENISSAMPEL: "Zona Sama"
    - Jika JNSZN tidak ada dalam daftar JENISSAMPEL: "Zona Beda"
    - Jika JENISSAMPEL kosong: "Tidak ada Jenis Zona Titik Sampel"
    """
    cursor = arcpy.da.UpdateCursor(zl, ["JNSZN", "JENISSAMPEL","BEDA_ZONA"])
    for row in cursor:
        JNSZN_str = str(row[0])  # Konversi JNSZN ke string
        jenissampel_list = []
        if row[1] is not None:
            # Memisahkan nilai JENISSAMPEL yang dipisahkan koma
            jenissampel_list = [x.strip() for x in row[1].split(",")]
        if JNSZN_str in jenissampel_list:
            row[2] = "Zona Sama"  # Menandai kesesuaian zona
        elif row[1] is not None: 
            row[2] = "Zona Beda"  # Menandai ketidaksesuaian zona
        else: 
            row[2] = "Tidak ada Jenis Zona Titik Sampel"  # Default value
        cursor.updateRow(row)
    del row, cursor

    """
    Tahap 3: Update data Titik Sampel berdasarkan Zona Layer
    - Melakukan spatial join antara Titik Sampel dan Zona Layer
    - Bergabung berdasarkan hubungan spasial INTERSECT
    - Menyinkronkan nilai Zoning di Titik Sampel dengan JNSZN di Zona Layer
    """
    arcpy.SpatialJoin_analysis(sampel, zl, out_temp, "JOIN_ONE_TO_MANY", "KEEP_ALL", "sync_id \"sync_id\" true true false 100 Text 0 0,First,#,sampel,sync_id,0,100; JNSZN \"JNSZN\" true true false 2 Short 0 0,First,#,zl,JNSZN,-1,-1", "INTERSECT")
    
    # Join field JNSZN dari temporary layer ke Titik_Sampel
    arcpy.JoinField_management(sampel, "OBJECTID", out_temp, "TARGET_FID", ["JNSZN"])
    
    # Update field Zoning di Titik_Sampel berdasarkan nilai JNSZN yang baru
    rows = arcpy.da.UpdateCursor(sampel, ["JNSZN", "Zoning"])
    for row in rows:
        if row[1] != row[0] and row[0] != None:
            row[1] = row[0]  # Update Zoning dengan nilai JNSZN
        rows.updateRow(row)
    del row, rows
    
    # Membersihkan field JNSZN yang telah di-join
    arcpy.DeleteField_management(sampel, "JNSZN")
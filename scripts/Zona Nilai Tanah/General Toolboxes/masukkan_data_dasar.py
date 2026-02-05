import os, arcpy, json
from sipentautils import zonalayer

# ======================
# ENVIRONMENT SETTINGS
# ======================
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# ======================
# PATH CONFIGURATION
# ======================

# Konfigurasi Path Aplikasi
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sim_zona = r"C:\PenilaianTanah\ui\symbology\Simbologi_Jenis_Zona.lyrx"

# Konfigurasi Path Project
zl_path = zonalayer.isZonaLayerComply()
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
config_path = os.path.join(ws_dir, "config.json")
configs = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        configs = json.load(f)

dataset_path = configs["dataset_path"]
THNNILAI = configs['THNNILAI']
WADMKK = configs['WADMKK']
WADMPR = configs['WADMPR']
coor = configs['coord']
gdb_path = configs['gdb_path']

# ======================
# USER INPUT
# ======================
in_features = arcpy.GetParameterAsText(0)

# ======================
# SET BACKUP
# ======================
tools_label = 'Pembuatan_ZNT-Persiapan_Data-Input_Data_Dasar'
zonalayer.saveGDB(ws_dir, gdb_path, label=tools_label)

# ======================
# MAIN PROCESSING
# ======================

"""
Mempersiapkan dan memproses feature class Zona_Layer untuk sistem penilaian tanah.
Termasuk konversi data, penambahan field, pengisian nilai default, dan validasi konsistensi data.
"""

# Mendapatkan daftar field OID dan semua field dari feature class input
id = [f.name for f in arcpy.ListFields (in_features, field_type="OID")]
fields = [f.name for f in arcpy.ListFields(in_features)]

"""
Menangani potensi konflik field OBJECTID:
- Beberapa data source mungkin memiliki field OBJECTID yang bukan true OID field
- Hapus field OBJECTID jika bukan field OID asli untuk menghindari duplikasi
- Ini penting untuk proses konversi ke geodatabase
"""
if 'OBJECTID' not in id and 'OBJECTID' in fields:
    arcpy.DeleteField_management (in_features, "OBJECTID")

"""
Mengkonversi feature class input ke geodatabase tujuan:
- in_features: data sumber yang akan dikonversi
- dataset_path: path ke geodatabase output
- 'Zona_Layer': nama feature class output
- Proses ini membuat salinan data dengan schema yang sesuai untuk processing selanjutnya
"""
arcpy.conversion.FeatureClassToFeatureClass(in_features, dataset_path, 'Zona_Layer')

# Mengatur coordinate system output untuk semua operasi berikutnya
arcpy.env.outputCoordinateSystem = coor

# Mendapatkan daftar field dari Zona_Layer yang sudah dikonversi
in_table_fields = [f.name for f in arcpy.ListFields(zl_path)]

"""
Menambahkan field-field required untuk sistem penilaian tanah jika belum ada:
Field-field ini diperlukan untuk analisis nilai tanah dan harus ada dalam schema
"""
if 'NOZN' not in in_table_fields:
    arcpy.management.AddField(zl_path, "NOZN", "LONG")  # Nomor Zona
    arcpy.management.AddField(zl_path, "PENGGUNAAN", "TEXT")  # Jenis Penggunaan Lahan
    arcpy.management.AddField(zl_path, "SMPBKREL", "DOUBLE")  # Sample Relative Value
    arcpy.management.AddField(zl_path, "SMPBAKU", "DOUBLE")  # Sample Standard Value
    arcpy.management.AddField(zl_path, "NILAIZN", "LONG")  # Nilai Zona
    arcpy.management.AddField(zl_path, "JMLSMPL", "DOUBLE")  # Jumlah Sample
    arcpy.management.AddField(zl_path, "NILMIN", "LONG")  # Nilai Minimum
    arcpy.management.AddField(zl_path, "NILMAKS", "LONG")  # Nilai Maksimum
    arcpy.management.AddField(zl_path, "WADMKK", "TEXT")  # Kode Administrasi Kabupaten
    arcpy.management.AddField(zl_path, "WADMPR", "TEXT")  # Kode Administrasi Provinsi
    arcpy.management.AddField(zl_path, "THNNILAI", "LONG")  # Tahun Penilaian
    arcpy.management.AddField(zl_path, "cluster", "TEXT")  # Cluster Zona

    arcpy.management.CalculateField(zl_path, "NOZN", "!OBJECTID!", "PYTHON3")

"""
Mengisi nilai default dari configuration:
- Nilai administrasi (WADMKK, WADMPR) dan tahun (THNNILAI) diambil dari config
- Cluster default di-set ke "1" untuk keperluan grouping
"""
arcpy.management.CalculateField(zl_path, "WADMKK", "'"+str(WADMKK)+"'", "PYTHON3")
arcpy.management.CalculateField(zl_path, "WADMPR", "'"+str(WADMPR)+"'", "PYTHON3")
arcpy.management.CalculateField(zl_path, "THNNILAI", THNNILAI, "PYTHON3")
arcpy.management.CalculateField(zl_path, "cluster", "1", "PYTHON3")

"""
Menangani field JNSZN (Jenis Zona):
- JNSZN: 1 = Non-Pertanian, 2 = Pertanian
- Jika field belum ada, tambahkan dan set default value ke 1
"""
if 'JNSZN' not in in_table_fields:
    arcpy.management.AddField(zl_path, "JNSZN", "SHORT")
    arcpy.management.CalculateField(zl_path, "JNSZN", "1", "PYTHON3")

"""
Mengisi default value untuk PENGGUNAAN jika field belum ada:
- Default value "Non-Pertanian" untuk konsistensi dengan JNSZN default
"""
if 'PENGGUNAAN' not in in_table_fields:
    arcpy.management.CalculateField(zl_path, "PENGGUNAAN", "'Non-Pertanian'", "PYTHON3")

arcpy.AddMessage(in_table_fields)
"""

Memastikan konsistensi antara field JNSZN dan PENGGUNAAN:
- UpdateCursor digunakan untuk iterasi dan update record secara efisien
- JNSZN = 1 → PENGGUNAAN = "Non-Pertanian"
- JNSZN = 2 → PENGGUNAAN = "Pertanian"
- rows.updateRow() menyimpan perubahan ke database
"""
with arcpy.da.UpdateCursor (zl_path, ["JNSZN", "PENGGUNAAN"]) as rows:
    for row in rows:
        if row[0] == 1:
            row[1] = "Non-Pertanian"
        elif row[0] == 2:
            row[1] = "Pertanian"
        rows.updateRow(row)

# Membersihkan cursor objects untuk menghindari memory leaks
del row
del rows

"""
Mengatur output parameter untuk tool geoprocessing:
- Parameter 1 adalah output feature class
- zl_path berisi path ke Zona_Layer yang sudah diproses
- Memungkinkan output digunakan dalam model builder atau proses chain berikutnya
"""
arcpy.SetParameter(1, zl_path)
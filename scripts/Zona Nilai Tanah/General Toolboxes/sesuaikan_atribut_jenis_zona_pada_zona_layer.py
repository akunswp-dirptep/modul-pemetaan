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
appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
ui_folder = os.path.join(appdata, "ui")
symbology_folder = os.path.join(ui_folder, "symbology")
# Konfigurasi Path Project
zl_path = zonalayer.isZonaLayerComply()  # Memeriksa dan mendapatkan path Zona Layer
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))  # Mendapatkan direktori workspace
config_path = os.path.join(ws_dir, "config.json")  # Path file konfigurasi
configs = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        configs = json.load(f)  # Memuat konfigurasi dari file JSON

# Mengambil nilai konfigurasi
dataset_path = configs['dataset_path']  # Path dataset utama

# ======================
# MAIN PROCESSING
# ======================

zl = "Zona_Layer"
jenis = arcpy.GetParameterAsText(0)

JENIS_ZONA = 1
if jenis == "Non-Pertanian":
    JENIS_ZONA = 1
elif jenis == "Pertanian":
    JENIS_ZONA = 2

if not arcpy.Exists(zl):
    arcpy.AddError("ERROR: Pengguna belum memasukkan data dasar.")
else:
    ada_seleksi = len(arcpy.Describe(zl).FIDSet)  
    if ada_seleksi > 0:
        try:
            with arcpy.da.UpdateCursor(zl, ["JNSZN", "PENGGUNAAN"]) as cursor:
                for row in cursor:
                    row[0] = JENIS_ZONA  # Mengupdate kolom JNSZN dengan kode numerik
                    row[1] = jenis       # Mengupdate kolom PENGGUNAAN dengan teks jenis
                    cursor.updateRow(row)  
        except Exception as e:

            if str(e) == 'Cannot acquire a lock.':
                arcpy.AddWarning(f'Tutup tabel atribut pada layer Zona_Layer sebelum menjalankan tool ini.')
            else:
                arcpy.AddWarning(f"ERROR: Terjadi kesalahan saat mengupdate atribut jenis zona. {e}")
  
    arcpy.CalculateField_management(
        zl, 
        "PENGGUNAAN", 
        f'"{jenis}"', 
        "PYTHON3", 
        ""
    )
zl_path = os.path.join(dataset_path, "Zona_Layer")
sim_path = os.path.join(symbology_folder, "Simbologi_Sesuaikan_Jenis_Zona.lyrx")

arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
arcpy.SetParameter(1, "Zona_Layer")
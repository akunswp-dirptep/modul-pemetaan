import arcpy, os, json
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

zl_path = os.path.join(dataset_path, "Zona_Layer")
ts_path = os.path.join(dataset_path, "Titik_Sampel")
tz_path = os.path.join(dataset_path, "Titik_Zona")
zl_temp_path = os.path.join(dataset_path, "Zona_Layer_Temp")
ts_temp_path = os.path.join(dataset_path, "Titik_Sampel_Temp")
tz_temp_path = os.path.join(dataset_path, "Titik_Zona_Temp")
zl_backup_path = os.path.join(dataset_path, "Zona_Layer_Backup")
ts_backup_path = os.path.join(dataset_path, "Titik_Sampel_Backup")
tz_backup_path = os.path.join(dataset_path, "Titik_Zona_Backup")
sim_path_zl = os.path.join(symbology_folder, "Simbologi_Peruntukan_Zona_Layer.lyrx")
sim_path_ts = os.path.join(symbology_folder, "Simbologi_Persebaran_Titik_Sampel.lyrx")
sim_path_tz = os.path.join(symbology_folder, "Simbologi_Persebaran_Titik_Zona.lyrx")

if not arcpy.Exists(zl_temp_path):
    arcpy.management.Copy(zl_path, zl_temp_path)

arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
arcpy.management.MakeFeatureLayer(ts_path, "Titik_Sampel")
arcpy.management.MakeFeatureLayer(tz_path, "Titik_Zona")
arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path_zl)
arcpy.management.ApplySymbologyFromLayer("Titik_Sampel", sim_path_ts)
arcpy.management.ApplySymbologyFromLayer("Titik_Zona", sim_path_tz)
arcpy.SetParameter(0, "Zona_Layer")
arcpy.SetParameter(1, "Titik_Sampel")
arcpy.SetParameter(2, "Titik_Zona")

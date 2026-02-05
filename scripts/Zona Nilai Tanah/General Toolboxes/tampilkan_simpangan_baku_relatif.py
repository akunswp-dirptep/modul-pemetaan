import sys, os, json, arcpy
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


# Mengambil nilai konfigurasi
dataset_path = configs['dataset_path']  # Path dataset utama

# Mengambil user input
pilihan = 'Utama'

if pilihan == 'Utama':
    zl_path = os.path.join(dataset_path, "Zona_Layer")
    if not arcpy.Exists(zl_path):
        arcpy.AddError('Zona Layer tidak ditemukan')
        sys.exit(1)
    sim_path = os.path.join(appdata, "Model_Pewarnaan_Simpangan_Baku_Relatif_ZNT.lyrx")

    arcpy.MakeFeatureLayer_management(zl_path, "Zona_Layer")
    arcpy.ApplySymbologyFromLayer_management("Zona_Layer", sim_path)
    arcpy.SetParameter(1, "Zona_Layer")

elif pilihan == 'Preview':
    zl_path = os.path.join(dataset_path, "Zona_Layer_Preview")
    if not arcpy.Exists(zl_path):
        arcpy.AddError('Preview tidak ditemukan')
        sys.exit(1)
    sim_path = os.path.join(appdata, "Model_Pewarnaan_Simpangan_Baku_Relatif_ZNT_Preview.lyrx")

    arcpy.MakeFeatureLayer_management(zl_path, "Zona_Layer_Preview")
    arcpy.ApplySymbologyFromLayer_management("Zona_Layer_Preview", sim_path)
    arcpy.SetParameter(1, "Zona_Layer_Preview")

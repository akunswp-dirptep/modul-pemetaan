import arcpy, os, json
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

# Konfigurasi Path Project
zl_path = zonalayer.isZonaLayerComply()
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
config_path = os.path.join(ws_dir, "config.json")
configs = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        configs = json.load(f)

dataset_path = configs['dataset_path']

# ======================
# MAIN PROCESSING
# ======================
# ts = Titik Sampel
# tsi = Titik Sampel Individual
tsi_path = os.path.join(dataset_path, "Titik_Sampel_Individual")
ts_path = os.path.join(dataset_path, "Titik_Sampel")
ui_folder = os.path.join(appdata, "ui")
symbology_folder = os.path.join(ui_folder, "symbology")
tsi_simbology_path = os.path.join(symbology_folder, "Titik_Sampel_Individual.lyrx")
ts_simbology_path = os.path.join(symbology_folder, "Titik_Sampel.lyrx")


arcpy.management.MakeFeatureLayer(ts_path, "Titik_Sampel")
arcpy.management.ApplySymbologyFromLayer("Titik_Sampel", ts_simbology_path)

if arcpy.Exists(tsi_path):
    arcpy.management.MakeFeatureLayer(tsi_path, "Titik_Sampel_Individual")
    arcpy.management.ApplySymbologyFromLayer("Titik_Sampel_Individual", tsi_simbology_path)

arcpy.SetParameter(0, "Titik_Sampel")
arcpy.SetParameter(1, "Titik_Sampel_Individual")

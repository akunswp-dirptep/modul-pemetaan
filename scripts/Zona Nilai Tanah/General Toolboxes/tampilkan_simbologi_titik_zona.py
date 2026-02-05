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

tz_path = os.path.join(dataset_path, "Titik_Zona")
ui_folder = os.path.join(appdata, "ui")
symbology_folder = os.path.join(ui_folder, "symbology")
tz_simbology_path = os.path.join(symbology_folder, "Titik_Zona.lyrx")


arcpy.management.MakeFeatureLayer(tz_path, "Titik_Zona")
arcpy.management.ApplySymbologyFromLayer("Titik_Zona", tz_simbology_path)

arcpy.SetParameter(0, "Titik_Zona")


import arcpy, os, json
from sipentautils import zonalayer

# ======================
# ENVIRONMENT SETTINGS
# ======================
arcpy.env.addOutputsToMap = True
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"
  

# ======================
# PATH CONFIGURATION
# ======================

# Konfigurasi Path Aplikasi
appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
ui_folder = os.path.join(appdata, "ui")
symbology_folder = os.path.join(ui_folder, "symbology")
simbology_path = os.path.join(symbology_folder, "Simbologi_Jenis_Zona.lyrx")

# Konfigurasi Path Project
zl_path = zonalayer.isZonaLayerComply()
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
config_path = os.path.join(ws_dir, "config.json")
arcpy.AddMessage(config_path)
configs = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        configs = json.load(f)

gdb = configs['dataset_path']
coor = configs['coord']

# ======================
# USER INPUT
# ======================
in_layer = arcpy.GetParameterAsText(0)

# ======================
# MAIN PROCESSING
# ======================
zl = "Zona_Layer"
arcpy.management.DefineProjection(in_layer, coor)
arcpy.SetParameter(1, in_layer)
arcpy.management.MakeFeatureLayer(zl_path, zl)
arcpy.management.ApplySymbologyFromLayer(zl, simbology_path)
arcpy.SetParameter(2, zl)
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
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Konfigurasi Path Project
zl_path = zonalayer.isZonaLayerComply()
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
config_path = os.path.join(ws_dir, "config.json")
configs = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        configs = json.load(f)

dataset_path = configs["dataset_path"]
gdb_path = configs['gdb_path']

# ======================
# UNSELECT FIELD 
# ======================

zonalayer.checkIfThereSelectedField()

# ======================
# MAIN PROCESSING
# ======================
zl = "Zona_Layer"
topo = 'Zona_Layer_Topology'
topologi = os.path.join(dataset_path, 'Zona_Layer_Topology')

if arcpy.Exists(topologi):
    arcpy.RemoveFeatureClassFromTopology_management (topologi, "Zona_Layer")

if arcpy.Exists(topo):
    arcpy.Delete_management(topo)

arcpy.AddField_management(zl, "Luas_M2", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED")
arcpy.CalculateField_management(zl, "Luas_M2", '!Shape.Area@meter!', "PYTHON3")


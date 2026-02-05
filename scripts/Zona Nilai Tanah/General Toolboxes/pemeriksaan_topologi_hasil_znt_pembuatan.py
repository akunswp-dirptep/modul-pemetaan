import os, arcpy, json
from sipentautils import zonalayer
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

lay_main = os.path.join(dataset_path, "Zona_Layer")
topo_name = 'Zona_Layer_Topology'
topologi_path = os.path.join(dataset_path, topo_name)

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

try:
    arcpy.management.CreateTopology(dataset_path, topo_name)
    arcpy.management.AddFeatureClassToTopology(topologi_path, lay_main, 1, 1)
    arcpy.management.AddRuleToTopology(topologi_path, "Must Not Have Gaps (Area)", lay_main)
    arcpy.management.AddRuleToTopology(topologi_path, "Must Not Overlap (Area)", lay_main)
    arcpy.management.ValidateTopology(topologi_path)
    arcpy.AddMessage("== Ada Error Topologi ==")
    aprx = arcpy.mp.ArcGISProject('CURRENT')
    current_map = aprx.activeMap
    current_map.addDataFromPath(topologi_path)

except:
    arcpy.AddMessage(arcpy.GetMessages())

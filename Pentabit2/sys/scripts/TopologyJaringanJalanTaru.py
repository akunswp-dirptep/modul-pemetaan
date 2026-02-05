import arcpy
import os

arcpy.AddMessage("== Proses dimulai ==")

jaringan_jalan = "Jaringan_Jalan"
JaringanJalanUpdate = "Jaringan_Jalan_Taru_Topo"
JaringanJalanTopo = "Topo_Jaringan_Jalan_Taru"
JaringanJalanTopoUpdate = "Topo_Jaringan_Jalan_Update"
JaringanJalanTopoAwal = "TopologiJaringanJalan"
JaringanJalanTopoKonsol = "Topo_Jaringan_Jalan_Konsolidasi"
dataset_path = ""

# Posisi sys
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
persil_conf_path = os.path.join(appdata, "jalan.dat")
conf_file = open(persil_conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

temp_gdb_path = os.path.join(appdata, "temporary.gdb")
topology_dataset_path = os.path.join(temp_gdb_path, "ds_topology")
# jarjaltop_path = os.path.join(topology_dataset_path, JaringanJalanTopo)
jarjaltop_path = os.path.join(dataset_path, JaringanJalanTopo)
jarjaltop_awal_path = os.path.join(dataset_path, JaringanJalanTopoAwal)
jarjaltop_update_path = os.path.join(dataset_path, JaringanJalanTopoUpdate)
# jarjalupd_path = os.path.join(topology_dataset_path, JaringanJalanUpdate)
jarjalupd_path = os.path.join(dataset_path, jaringan_jalan)

# jaringan_jalan_path = arcpy.GetParameterAsText(0)

# arcpy.AddMessage(temp_gdb_path)
# arcpy.AddMessage(topology_dataset_path)
# arcpy.AddMessage(jarjaltop_path)

if arcpy.Exists(jarjaltop_path):
    arcpy.Delete_management(jarjaltop_path)
if arcpy.Exists(jarjaltop_awal_path):
    arcpy.Delete_management(jarjaltop_awal_path)
if arcpy.Exists(jarjaltop_update_path):
    arcpy.Delete_management(jarjaltop_update_path)
# if arcpy.Exists(jarjalupd_path):
#     arcpy.Delete_management(jarjalupd_path)
if arcpy.Exists(JaringanJalanTopo):
    arcpy.Delete_management(JaringanJalanTopo)
if arcpy.Exists(JaringanJalanTopoAwal):
    arcpy.Delete_management(JaringanJalanTopoAwal)
if arcpy.Exists(JaringanJalanTopoUpdate):
    arcpy.Delete_management(JaringanJalanUpdate)

# arcpy.FeatureClassToFeatureClass_conversion(jaringan_jalan_path, topology_dataset_path, JaringanJalanUpdate)

arcpy.CreateTopology_management(dataset_path, JaringanJalanTopo)
arcpy.AddFeatureClassToTopology_management(jarjaltop_path, jarjalupd_path, 1, 1)
arcpy.AddRuleToTopology_management(jarjaltop_path, "Must Not Overlap (Line)", jarjalupd_path)
arcpy.AddRuleToTopology_management(jarjaltop_path, "Must Not Have Dangles (Line)", jarjalupd_path)
arcpy.AddRuleToTopology_management(jarjaltop_path, "Must Not Have Pseudo-Nodes (Line)", jarjalupd_path)
arcpy.ValidateTopology_management(jarjaltop_path)

if arcpy.Exists(JaringanJalanTopo):
    arcpy.Delete_management(JaringanJalanTopo)

arcpy.SetParameterAsText(0, jarjaltop_path)

arcpy.AddMessage("== Proses selesai ==")

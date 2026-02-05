import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

jaringan_jalan = "Jaringan_Jalan"
dataset_path = ""

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

jaringan_jalan_path = os.path.join(dataset_path, jaringan_jalan)

if arcpy.Exists(os.path.join(dataset_path, "Topo_Jaringan_Jalan_Taru")):
    arcpy.Delete_management(os.path.join(dataset_path, "Topo_Jaringan_Jalan_Taru"))
if arcpy.Exists(os.path.join(dataset_path, "Topo_Jaringan_Jalan_Konsol")):
    arcpy.Delete_management(os.path.join(dataset_path, "Topo_Jaringan_Jalan_Konsol"))
if arcpy.Exists(os.path.join(dataset_path, "Topo_Jaringan_Jalan")):
    arcpy.Delete_management(os.path.join(dataset_path, "Topo_Jaringan_Jalan"))

# tempdata = os.path.join(appdata, "temp")
# no_sim_path = os.path.join(appdata, "SimbologiJaringanJalanUpdate.lyr")

# out_shp = "Jaringan_Jalan_Konsolidasi"
# out_path = os.path.join(tempdata, out_shp)
# out_path = os.path.join(dataset_path, out_shp)

arcpy.AddMessage("== Tambah field status_jal ==")

list_names = [f.name for f in arcpy.ListFields(jaringan_jalan_path)]
if "status_jal" not in list_names:
    arcpy.AddField_management(jaringan_jalan_path, "status_jal", "Text")

arcpy.CalculateField_management(jaringan_jalan_path, "status_jal", "'Tetap'", "PYTHON")

# with arcpy.da.UpdateCursor(jaringan_jalan_path, "status_jal") as cur:
#     for row in cur:
#         if row[0] != "Update":
#             row[0] = "Tetap"
#             cur.updateRow(row)

# arcpy.AddMessage("== Pindahkan shapefile ke temp ==")

# if arcpy.Exists(out_path):
#     arcpy.Delete_management(out_path)
#
# arcpy.CopyFeatures_management(in_jaringan_jalan, out_path)

if arcpy.Exists(jaringan_jalan):
    arcpy.Delete_management(jaringan_jalan)

arcpy.MakeFeatureLayer_management(jaringan_jalan_path, jaringan_jalan)
# arcpy.ApplySymbologyFromLayer_management(jaringan_jalan, no_sim_path)

arcpy.SetParameterAsText(0, jaringan_jalan)

arcpy.AddMessage("== Proses selesai ==")

import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "jalan.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
topologi = ""
topologi_path = ""
jaringanjalan_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]
    if jalan_config[0] == "topologi_jaringanjalan":
        topologi = jalan_config[1].split(";")[0]
        topologi_path = jalan_config[1].split(";")[1]
    if jalan_config[0] == "jaringanjalan":
        jaringanjalan_path = jalan_config[1].split(";")[1]

arcpy.AddMessage("== Buat topologi jaringan jalan ==")

if arcpy.Exists(topologi_path):
    arcpy.Delete_management(topologi_path)

arcpy.CreateTopology_management(dataset_path, topologi)
arcpy.AddFeatureClassToTopology_management(topologi_path, jaringanjalan_path, 1, 1)
arcpy.AddRuleToTopology_management(topologi_path, "Must Not Overlap (Line)", jaringanjalan_path)
arcpy.AddRuleToTopology_management(topologi_path, "Must Not Have Dangles (Line)", jaringanjalan_path)
arcpy.AddRuleToTopology_management(topologi_path, "Must Not Have Pseudo-Nodes (Line)", jaringanjalan_path)
arcpy.ValidateTopology_management(topologi_path)

if arcpy.Exists(topologi):
    arcpy.Delete_management(topologi)

arcpy.SetParameterAsText(0, topologi_path)

arcpy.AddMessage("== Menjalankan proses berhasil dilakukan. Silakan lanjutkan proses berikutnya... ==")

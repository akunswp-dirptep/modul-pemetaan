import os
import arcpy

resiko_path = arcpy.GetParameterAsText(0)
a = arcpy.GetParameterAsText(1)
arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_path = os.path.join(appdata, "config.dat")
conf_resiko_path = os.path.join(appdata, "resiko.dat")
conf_jalan_path = os.path.join(appdata, "jalan.dat")

conf_file = open(conf_resiko_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
gdb_path = ""
jalan_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "datasetresiko":
        dataset_path = persil_config[1]

conf_file = open(conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "gdb":
        gdb_path = persil_config[1]

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "jaringanjalan":
        jalan_path = persil_config[1].split(";")[1]

# resiko = os.path.basename(resiko_path).split(".")[0]
if a == "Banjir":
    resiko = "banjir"
elif a == "Longsor":
    resiko = "longsor"
elif a == "Risiko 1":
    resiko = "risiko_1"
elif a == "Risiko 2":
    resiko = "risiko_2"

if not arcpy.Exists(dataset_path):
    arcpy.CreateFeatureDataset_management(gdb_path, "resiko", jalan_path)

if arcpy.Exists(os.path.join(dataset_path, resiko)):
    arcpy.Delete_management(os.path.join(dataset_path, resiko))
if arcpy.Exists(resiko):
    arcpy.Delete_management(resiko)

arcpy.FeatureClassToFeatureClass_conversion(resiko_path, dataset_path, resiko)

arcpy.MakeFeatureLayer_management(os.path.join(dataset_path, resiko), resiko)
arcpy.SetParameterAsText(2, resiko)

arcpy.AddMessage("== Proses selesai ==")

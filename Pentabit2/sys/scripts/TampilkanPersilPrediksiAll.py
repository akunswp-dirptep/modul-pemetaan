import os
import arcpy

prediksiall_path = arcpy.GetParameterAsText(0)

arcpy.AddMessage("== Proses dimulai ==")

appdata = 'c:\znt\sys'
conf_jalan_path = os.path.join(appdata, "jalan.dat")
conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

targrt_path = os.path.join(dataset_path, "PersilPrediksiAll")

if arcpy.Exists(targrt_path):
    arcpy.Delete_management(targrt_path)

arcpy.FeatureClassToFeatureClass_conversion(prediksiall_path, dataset_path, "PersilPrediksiAll")

arcpy.AddMessage("== Proses selesai ==")

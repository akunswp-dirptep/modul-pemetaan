import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "jalan.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
jaringanjalan = ""
jaringanjalan_path = ""
simbologi_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]
    if jalan_config[0] == "jaringanjalan":
        jaringanjalan = jalan_config[1].split(";")[0]
        jaringanjalan_path = jalan_config[1].split(";")[1]
    if jalan_config[0] == "simbologikelasjalan":
        simbologi_path = jalan_config[1].split(";")[1]

jaringanjalan = "Jaringan_Jalan"
jaringanjalan_path = os.path.join(dataset_path, jaringanjalan)

if arcpy.Exists("temp"):
    arcpy.Delete_management("temp")

arcpy.MakeFeatureLayer_management(jaringanjalan_path, "temp")
arcpy.SelectLayerByAttribute_management("temp", "NEW_SELECTION", "kls_jln IS NULL")
arcpy.CalculateField_management("temp", "kls_jln", "'Lokal'", "PYTHON")
arcpy.CalculateField_management("temp", "s_kls_jln", "1", "PYTHON")

if arcpy.Exists("temp"):
    arcpy.Delete_management("temp")

if arcpy.Exists(jaringanjalan):
    arcpy.Delete_management(jaringanjalan)
if arcpy.Exists("Jaringan_Jalan"):
    arcpy.Delete_management("Jaringan_Jalan")

arcpy.MakeFeatureLayer_management(jaringanjalan_path, jaringanjalan)
arcpy.ApplySymbologyFromLayer_management(jaringanjalan, simbologi_path)

arcpy.SetParameterAsText(0, jaringanjalan)

arcpy.AddMessage("== Proses selesai ==")

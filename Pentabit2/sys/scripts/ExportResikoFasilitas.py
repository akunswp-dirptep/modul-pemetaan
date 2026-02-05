import os
import arcpy

out_path = arcpy.GetParameterAsText(0)

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_resiko_path = os.path.join(appdata, "resiko.dat")
conf_fasilitas_path = os.path.join(appdata, "fasilitas.dat")

datasetfasilitas_path = ""
datasetresiko_path = ""

conf_file = open(conf_fasilitas_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    config = []
    config = line.split(",")
    if config[0] == "datasetfasilitas":
        datasetfasilitas_path = config[1]

conf_file = open(conf_resiko_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    config = []
    config = line.split(",")
    if config[0] == "datasetresiko":
        datasetresiko_path = config[1]

arcpy.env.workspace = datasetfasilitas_path
list_fc = arcpy.ListFeatureClasses("*")
list_to_copy = []

for fc in list_fc:
    if arcpy.Exists(os.path.join(out_path, fc)):
        arcpy.Delete_management(os.path.join(out_path, fc))
    list_to_copy.append(os.path.join(datasetfasilitas_path, fc))

# arcpy.FeatureClassToShapefile_conversion(list_to_copy, out_path)

arcpy.env.workspace = datasetresiko_path
list_fc = arcpy.ListFeatureClasses("*")
# list_to_copy = []

for fc in list_fc:
    if arcpy.Exists(os.path.join(out_path, fc)):
        arcpy.Delete_management(os.path.join(out_path, fc))
    list_to_copy.append(os.path.join(datasetresiko_path, fc))

arcpy.FeatureClassToShapefile_conversion(list_to_copy, out_path)

arcpy.AddMessage("== Proses Selesai ==")

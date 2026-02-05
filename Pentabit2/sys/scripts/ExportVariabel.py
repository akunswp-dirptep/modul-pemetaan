import os
import arcpy

out = arcpy.GetParameterAsText(0)
# shp = arcpy.GetParameterAsText(1)

arcpy.env.overwriteOutput = True

# if ".shp" not in shp:
#     shp = shp + ".shp"

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

# sampel_path = os.path.join(dataset_path, "PersilSampelPrediksi")
sampel_path = os.path.join(dataset_path, "Sampel_Model")

shp = "sampel_model.shp"
output = os.path.join(out, shp)

if arcpy.Exists(output):
    arcpy.Delete_management(output)

arcpy.CopyFeatures_management(sampel_path, os.path.join(out, shp))
# arcpy.FeatureClassToShapefile_conversion([sampel_path], out)

arcpy.AddMessage("== Proses selesai ==")

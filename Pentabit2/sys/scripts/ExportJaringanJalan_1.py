import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

out = arcpy.GetParameterAsText(0)
# shp = arcpy.GetParameterAsText(1)

arcpy.env.overwriteOutput = True

# if ".shp" not in shp:
#     shp = shp + ".shp"

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "jalan.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

jaringanjalan = ""
jaringanjalan_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]
    if jalan_config[0] == "jaringanjalan":
        jaringanjalan = jalan_config[1].split(";")[0]
        jaringanjalan_path = jalan_config[1].split(";")[1]

shp = "jaringan_jalan.shp"
output = os.path.join(out, shp)

exp = "get(!S_KlsJln!, !L_Jalan!)"
code_block = """
def get(b,c):
    if b == 5:
        if c < 11:
            return 11
    if b == 4:
        if c < 8:
            return 8
    if b == 3:
        if c < 6:
            return 6
    if b == 2:
        if c < 5:
            return 5"""
arcpy.CalculateField_management(jaringanjalan_path, 'L_Jalan', exp, "PYTHON", code_block)

if arcpy.Exists(output):
    arcpy.Delete_management(output)

arcpy.CopyFeatures_management(jaringanjalan_path, os.path.join(out, shp))
# arcpy.FeatureClassToShapefile_conversion([jaringanjalan_path], out)

arcpy.AddMessage("== Proses selesai ==")

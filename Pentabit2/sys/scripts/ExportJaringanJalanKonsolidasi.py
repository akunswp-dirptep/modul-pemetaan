import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "jalan.dat")
conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

list_err = []
dataset_path = ""
jaringanjalan_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

out = arcpy.GetParameterAsText(0)
kab_kota = arcpy.GetParameterAsText(1)
nama_kab_kota = arcpy.GetParameterAsText(2)
tahun=arcpy.GetParameter(3)
# shp = arcpy.GetParameterAsText(1)

arcpy.env.overwriteOutput = True

# if ".shp" not in shp:
#     shp = shp + ".shp"

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
tempdata = os.path.join(appdata, "temp")

jaringanjalan = "Jaringan_Jalan"
jaringanjalan_path = os.path.join(dataset_path, jaringanjalan)

if arcpy.Exists(os.path.join(dataset_path, "Topo_Jaringan_Jalan_Taru")):
    arcpy.Delete_management(os.path.join(dataset_path, "Topo_Jaringan_Jalan_Taru"))
if arcpy.Exists(os.path.join(dataset_path, "Topo_Jaringan_Jalan")):
    arcpy.Delete_management(os.path.join(dataset_path, "Topo_Jaringan_Jalan"))
if arcpy.Exists(os.path.join(dataset_path, "Topo_Jaringan_Jalan_Konsolidasi")):
    arcpy.Delete_management(os.path.join(dataset_path, "Topo_Jaringan_Jalan_Konsolidasi"))
if arcpy.Exists(os.path.join(dataset_path, "Topo_Jaringan_Jalan_Update")):
    arcpy.Delete_management(os.path.join(dataset_path, "Topo_Jaringan_Jalan_Update"))

# if arcpy.Exists(jaringanjalan):
#     arcpy.Delete_management(jaringanjalan)
#
# arcpy.MakeFeatureLayer_management(jaringanjalan_path, jaringanjalan)

shp = "Peta Jaringan Jalan " + kab_kota + " " + nama_kab_kota + " Tahun " + str(tahun) + ".shp"
output = os.path.join(out, shp)

edit = arcpy.da.Editor(os.path.dirname(dataset_path))
edit.startEditing(False, False)
edit.startOperation()

with arcpy.da.UpdateCursor(jaringanjalan_path, ["s_kls_jln", "lb_jln"]) as cur:
    for row in cur:
        if row[0] == 5:
            if row[1] < 11:
                row[1] = 11
        if row[0] == 4:
            if row[1] < 8:
                row[1] = 8
        if row[0] == 3:
            if row[1] < 6:
                row[1] = 6
        if row[0] == 2:
            if row[1] < 5:
                row[1] = 5
        if row[0] == 1:
            if row[1] < 1.5:
                row[1] = 1.5
        cur.updateRow(row)

edit.stopOperation()
edit.stopEditing(True)

# exp = "get(!s_kls_jln!, !lb_jln!)"
# code_block = """
# def get(b,c):
#     if b == 5:
#         if c < 11:
#             return 11
#     if b == 4:
#         if c < 8:
#             return 8
#     if b == 3:
#         if c < 6:
#             return 6
#     if b == 2:
#         if c < 5:
#             return 5
#     if b == 1:
#         if c < 1.5:
#             return 1.5"""
# arcpy.CalculateField_management(jaringanjalan, u'lb_jln', exp, "PYTHON", code_block)

if arcpy.Exists(output):
    arcpy.Delete_management(output)

# if arcpy.Exists(os.path.join(dataset_path, jaringanjalan)):
#     arcpy.Delete_management(os.path.join(dataset_path, jaringanjalan))

# arcpy.CopyFeatures_management(jaringanjalan_path, os.path.join(dataset_path, jaringanjalan))
arcpy.CopyFeatures_management(jaringanjalan_path, os.path.join(out, shp))
# arcpy.FeatureClassToShapefile_conversion([jaringanjalan_path], out)

arcpy.AddMessage("== Proses selesai ==")

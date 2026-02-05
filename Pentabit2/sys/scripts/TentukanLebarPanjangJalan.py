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
jaringanjalan_path = ""
sisijalan_path = ""
midpointjaringanjalan_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]
    if jalan_config[0] == "sisijalan":
        sisijalan_path = jalan_config[1].split(";")[1]
    if jalan_config[0] == "jaringanjalan":
        jaringanjalan_path = jalan_config[1].split(";")[1]
    if jalan_config[0] == "midpointjaringanjalan":
        midpointjaringanjalan_path = jalan_config[1].split(";")[1]

if arcpy.Exists(midpointjaringanjalan_path):
    arcpy.Delete_management(midpointjaringanjalan_path)

arcpy.AddMessage("== Hitung Lebar Jalan ==")

field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]
if 'SimLJln2' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 'SimLJln2', 'TEXT')
if 'lb_jln' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 'lb_jln', 'DOUBLE')
if 'P_Jalan' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 'P_Jalan', 'DOUBLE')

arcpy.CalculateField_management(jaringanjalan_path, "P_Jalan", "!shape.length!", "PYTHON")

arcpy.FeatureToPoint_management(jaringanjalan_path, midpointjaringanjalan_path, "INSIDE")
arcpy.Near_analysis(midpointjaringanjalan_path, [sisijalan_path], 100, "LOCATION", "NO_ANGLE")

field_names = [field.name for field in arcpy.ListFields(midpointjaringanjalan_path)]
if 'lb_jln' not in field_names:
    arcpy.AddField_management(midpointjaringanjalan_path, 'lb_jln', 'DOUBLE')
#update 13/10/2021
#arcpy.CalculateField_management(midpointjaringanjalan_path, "lb_jln", "2 * [NEAR_DIST]", "VB")
arcpy.CalculateField_management(midpointjaringanjalan_path, "lb_jln", "2 * !NEAR_DIST!", "PYTHON")

cur1 = arcpy.SearchCursor(midpointjaringanjalan_path)

for row1 in cur1:
    cur2 = arcpy.UpdateCursor(jaringanjalan_path, 'OBJECTID=' + repr(row1.ORIG_FID))
    for row2 in cur2:
        row2.lb_jln = row1.lb_jln
        if row2.lb_jln > 30:
            row2.lb_jln = 30
        if row2.lb_jln < 0:
            row2.lb_jln = 0
        if row1.lb_jln <= 0:
            row2.SimLJln2 = "0"
        elif row1.lb_jln > 0 and row1.lb_jln <= 1.5:
            row2.SimLJln2 = "1.5"
        elif row1.lb_jln > 1.5 and row1.lb_jln <= 3:
            row2.SimLJln2 = "3"
        elif row1.lb_jln > 3 and row1.lb_jln <= 5:
            row2.SimLJln2 = "5"
        elif row1.lb_jln > 5 and row1.lb_jln <= 8:
            row2.SimLJln2 = "8"
        else:
            row2.SimLJln2 = "8+"
        cur2.updateRow(row2)
    del cur2
del cur1

arcpy.AddMessage("== Selesai Hitung Lebar Jalan ==")

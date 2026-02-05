import os, sys
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

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]
    if jalan_config[0] == "jaringanjalan":
        jaringanjalan = jalan_config[1].split(";")[0]
        jaringanjalan_path = jalan_config[1].split(";")[1]

lebarjalan = arcpy.GetParameter(0)

field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]
if 'lb_jln' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 'lb_jln', 'DOUBLE')
if 'Sim_LJln' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 'Sim_LJln', 'TEXT')
if 'SimLJln2' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 'SimLJln2', "TEXT")

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(jaringanjalan).FIDSet)

if ada_seleksi <= 0:
    sys.exit()

#edit = arcpy.da.Editor(os.path.dirname(dataset_path))
#edit.startEditing(False, False)
#edit.startOperation()

rows = arcpy.UpdateCursor(jaringanjalan)

for row in rows:
    row.lb_jln = lebarjalan
    if lebarjalan == 0:
        row.SimLJln2 = "0"
    elif lebarjalan > 0 and lebarjalan <= 1.5:
        row.SimLJln2 = "1.5"
    elif lebarjalan > 1.5 and lebarjalan <= 3:
        row.SimLJln2 = "3"
    elif lebarjalan > 3 and lebarjalan <= 5:
        row.SimLJln2 = "5"
    elif lebarjalan > 5 and lebarjalan  <= 8:
        row.SimLJln2 = "8"
    elif lebarjalan > 8:
        row.SimLJln2 = "8+"
    rows.updateRow(row)

del row
del rows

#edit.stopOperation()
#edit.stopEditing(True)

#edit 10/10/22
arcpy.CalculateField_management(jaringanjalan, "lb_jln" , lebarjalan , "PYTHON3", "")
arcpy.AddMessage("== Proses selesai ==")

#update 13/10/2021
#arcpy.RefreshTOC()
#arcpy.RefreshActiveView()

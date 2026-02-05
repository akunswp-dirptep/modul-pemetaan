import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
persil = ""
persil_path = ""
simbologi_path = os.path.join(appdata, "SimbologiLebarJalanUpdate2_i3.lyr")

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]

lebarjalan = arcpy.GetParameter(0)

arcpy.AddMessage(lebarjalan)

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'lb_jln' not in field_names:
    arcpy.AddField_management(persil_path, 'lb_jln', 'DOUBLE')

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'SimLJln2' not in field_names:
    arcpy.AddField_management(persil_path, 'SimLJln2', "TEXT")

with arcpy.da.UpdateCursor(persil, ["lb_jln", "SimLJln2"]) as rows:
    for row in rows:
        row[0] = lebarjalan
        if lebarjalan == 0:
            row[1] = "0"
        elif lebarjalan > 0 and lebarjalan <= 1.5:
            row[1] = "1.5"
        elif lebarjalan > 1.5 and lebarjalan <= 3:
            row[1] = "3"
        elif lebarjalan > 3 and lebarjalan <= 5:
            row[1] = "5"
        elif lebarjalan > 5 and lebarjalan <= 8:
            row[1] = "8"
        elif lebarjalan > 8:
            row[1] = "8+"
        rows.updateRow(row)
del rows, row

#rows = arcpy.UpdateCursor(persil)

#for row in rows:
#    row.L_Jalan = lebarjalan
#    if lebarjalan == 0:
#        row.SimLJln = "0"
#    elif lebarjalan > 0 and lebarjalan <= 1:
#        row.SimLJln = "1"
#    elif lebarjalan > 1 and lebarjalan <= 2:
#        row.SimLJln = "2"
#    else:
#        row.SimLJln = "3"
#    rows.updateRow(row)

#del row
#del rows

if arcpy.Exists(persil):
    arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

#update 16/10/2021
#arcpy.RefreshTOC()
#arcpy.RefreshActiveView()

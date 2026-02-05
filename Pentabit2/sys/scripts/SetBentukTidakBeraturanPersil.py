import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = 'c:\znt\sys'
conf_persil_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
persil = ""
persil_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'Bentuk' not in field_names:
    arcpy.AddField_management(persil_path, 'Bentuk', 'DOUBLE')
if 'SkorBentuk' not in field_names:
    arcpy.AddField_management(persil_path, 'SkorBentuk', 'SHORT')

rows = arcpy.UpdateCursor(persil)

for row in rows:
    row.Bentuk = "Segi Banyak Tidak Beraturan"
    row.SkorBentuk = 1
    rows.updateRow(row)

del row
del rows

arcpy.RefreshTOC()
arcpy.RefreshActiveView()

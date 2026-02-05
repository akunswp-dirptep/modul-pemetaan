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
simbologi_path = os.path.join(appdata, "SimbologiLebarJalanUpdate2_i3.lyr")

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

persil = "Persil_Konsolidasi"
persil_path = os.path.join(dataset_path, persil)

persil_fields = [f.name for f in arcpy.ListFields(persil_path)]

if "SimLJln2" not in persil_fields:
    arcpy.AddField_management(persil_path, "SimLJln2", "TEXT")

with arcpy.da.UpdateCursor(persil_path, ["lb_jln", "SimLJln2"]) as rows:
    for row in rows:
        if row[0] == 0:
            row[1] = "0"
        elif row[0] > 0 and row[0] <= 1.5:
            row[1] = "1.5"
        elif row[0] > 1.5 and row[0] <= 3:
            row[1] = "3"
        elif row[0] > 3 and row[0] <= 5:
            row[1] = "5"
        elif row[0] > 5 and row[0] <= 8:
            row[1] = "8"
        elif row[0] > 8:
            row[1] = "8+"
        rows.updateRow(row)
del rows, row

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)

arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

arcpy.SetParameterAsText(0, persil)

arcpy.AddMessage("== Proses selesai ==")

import os
import arcpy, arcpy.mp


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

persil = "Persil_Baru"
persil_path = os.path.join(dataset_path, persil)
persil_baru = "Persil_Baru"
persil_baru_path = os.path.join(dataset_path, persil_baru)

persil_fields = [field.name for field in arcpy.ListFields(persil_path)]
if "SimLJln2" not in persil_fields:
    arcpy.AddField_management(persil_path, "SimLJln2", "TEXT")

# edit = arcpy.da.Editor(os.path.dirname(dataset_path))
# edit.startEditing(False, False)
# edit.startOperation()
with arcpy.da.UpdateCursor(persil_path, ["lb_jln", "SimLJln2"]) as rows:
    for row in rows:
        if not row[0]:
            row[0] = 0
            row[1] = "0"
        else:
            if row[0] > 30:
                row[0] = 30
                row[1] = "8+"
            else:
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


persil_fields = [f.name for f in arcpy.ListFields(persil_baru_path)]

if "SimLJln2" not in persil_fields:
    arcpy.AddField_management(persil_baru_path, "SimLJln2", "TEXT")

with arcpy.da.UpdateCursor(persil_baru_path, ["lb_jln", "SimLJln2"]) as rows:
    for row in rows:
        if not row[0]:
            row[0] = 0
            row[1] = "0"
        else:
            if row[0] > 30:
                row[0] = 30
                row[1] = "8+"
            else:
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

# edit.stopOperation()
# edit.stopEditing(True)

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)

arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

jaringanjalan = "Jaringan_Jalan"
jaringanjalan_path = os.path.join(dataset_path, jaringanjalan)
if arcpy.Exists(jaringanjalan):
    arcpy.Delete_management(jaringanjalan)

simbologi_path = os.path.join(appdata, "SimbologiLebarJalanUpdate.lyr")
arcpy.MakeFeatureLayer_management(jaringanjalan_path, jaringanjalan)
arcpy.ApplySymbologyFromLayer_management(jaringanjalan, simbologi_path)

arcpy.SetParameterAsText(1, jaringanjalan)

arcpy.SetParameterAsText(0, persil)


aprx = arcpy.mp.ArcGISProject("CURRENT")
map = aprx.activeMap
layers = map.listLayers()
for layer in layers:
    if layer.name == "JaringanJalanForND":
        layer.visible = False

arcpy.AddMessage("== Proses selesai ==")

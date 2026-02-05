import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
tempdata = os.path.join(appdata, "temp")

dataset_path = ""

conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()
for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

persil_update = "Persil_Konsolidasi"

lb_jln = arcpy.GetParameter(0)
SimLJln2 = "0"

persil_fields = [f.name for f in arcpy.ListFields(persil_update)]

if "SimLJln2" not in persil_fields:
    arcpy.AddField_management(persil_update, "SimLJln2", "TEXT")

if lb_jln == 0:
    SimLJln2 = "0"
elif lb_jln > 0 and lb_jln <= 1.5:
    SimLJln2 = "1.5"
elif lb_jln > 1.5 and lb_jln <= 3:
    SimLJln2 = "3"
elif lb_jln > 3 and lb_jln <= 5:
    SimLJln2 = "5"
elif lb_jln > 5 and lb_jln <= 8:
    SimLJln2 = "8"
elif lb_jln > 8:
    SimLJln2 = "8+"

if "lb_jln" not in persil_fields :
    arcpy.AddError("Field " + "lb_jln" + " tidak ditemukan.")
    raise arcpy.ExecuteError

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(persil_update).FIDSet)
if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(persil_update)
    for row in rows:
        row.setValue("lb_jln", lb_jln)
        row.setValue("SimLJln2", SimLJln2)
        rows.updateRow(row)

    del row
    del rows

arcpy.RefreshTOC()
arcpy.RefreshActiveView()

arcpy.AddMessage("== Proses selesai ==")

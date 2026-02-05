import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

persil_update = "Persil_Taru"
SimLbDpn = "3"

lb_dpn = arcpy.GetParameter(0)

if lb_dpn >= 0 and lb_dpn <= 3:
    SimLbDpn = "3"
elif lb_dpn > 3:
    SimLbDpn = "3+"

fields = [f.name for f in arcpy.ListFields(persil_update)]
if "SimLbDpn" not in fields:
    arcpy.AddField_management(persil_update, "SimLbDpn", "TEXT")

if "lb_dpn" not in fields :
    arcpy.AddError("Field " + "lb_dpn" + " tidak ditemukan.")
    raise arcpy.ExecuteError

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(persil_update).FIDSet)

if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(persil_update)
    for row in rows:
        row.setValue("lb_dpn", lb_dpn)
        row.setValue("SimLbDpn", SimLbDpn)
        rows.updateRow(row)

    del row
    del rows

arcpy.RefreshTOC()
arcpy.RefreshActiveView()

arcpy.AddMessage("== Proses selesai ==")

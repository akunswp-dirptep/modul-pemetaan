import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
tempdata = os.path.join(appdata, "temp")

persil_update = "Persil_Konsolidasi"

persil_fields = [f.name for f in arcpy.ListFields(persil_update)]

if "SimLJln2" not in persil_fields:
    arcpy.AddField_management(persil_update, "SimLJln2", "TEXT")

kls_jln = arcpy.GetParameterAsText(0)
lb_jln = arcpy.GetParameter(1)
status = arcpy.GetParameterAsText(2)
s_kls_jln = 1

simjln = "0"
if lb_jln == 0:
    simjln = "0"
elif lb_jln > 0 and lb_jln <= 1.5:
    simjln = "1.5"
elif lb_jln > 1.5 and lb_jln <= 3:
    simjln = "3"
elif lb_jln > 3 and lb_jln <= 5:
    simjln = "5"
elif lb_jln > 5 and lb_jln <= 8:
    simjln = "8"
elif lb_jln > 8:
    simjln = "8+"

if kls_jln == "Arteri Primer":
    s_kls_jln = 5
elif kls_jln == "Arteri Sekunder":
    s_kls_jln = 4
elif kls_jln == "Kolektor Primer":
    s_kls_jln = 3
elif kls_jln == "Kolektor Sekunder":
    s_kls_jln = 2
else:
    s_kls_jln = 1

persil_fields = [f.name for f in arcpy.ListFields(persil_update)]

if "kls_jln" not in persil_fields or "lb_jln" not in persil_fields or "s_kls_jln" not in persil_fields:
    arcpy.AddError("Field " + "kls_jln, lb_jln, s_kls_jln" + " tidak ditemukan.")
    raise arcpy.ExecuteError

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(persil_update).FIDSet)
if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(persil_update)
    for row in rows:
        row.setValue("kls_jln", kls_jln)
        row.setValue("lb_jln", lb_jln)
        row.setValue("SimLJln2", simjln)
        row.setValue("s_kls_jln", s_kls_jln)
        row.setValue("obj_konsol", status)
        rows.updateRow(row)

    del row
    del rows

arcpy.RefreshTOC()
arcpy.RefreshActiveView()

arcpy.AddMessage("== Proses selesai ==")

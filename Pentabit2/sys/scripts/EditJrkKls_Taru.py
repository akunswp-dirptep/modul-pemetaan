import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
tempdata = os.path.join(appdata, "temp")

persil_update = "Persil_Taru"

persil_fields = [f.name for f in arcpy.ListFields(persil_update)]

kls_jln = arcpy.GetParameterAsText(0)
jrk_jln = arcpy.GetParameter(1)
field = "jk_atrp"

if kls_jln == "Arteri Primer":
    field = "jk_atrp"
elif kls_jln == "Arteri Sekunder":
    field = "jk_atrs"
elif kls_jln == "Kolektor Primer":
    field = "jk_kolp"
elif kls_jln == "Kolektor Sekunder":
    field = "jk_kols"

persil_fields = [f.name for f in arcpy.ListFields(persil_update)]

if field not in persil_fields:
    arcpy.AddError("Field " + field + " tidak ditemukan.")
    raise arcpy.ExecuteError

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(persil_update).FIDSet)
if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(persil_update)
    for row in rows:
        row.setValue(field, jrk_jln)
        rows.updateRow(row)
    del row
    del rows

arcpy.RefreshTOC()
arcpy.RefreshActiveView()

arcpy.AddMessage("== Proses selesai ==")

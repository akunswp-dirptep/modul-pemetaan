import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
tempdata = os.path.join(appdata, "temp")

persil_baru = "Persil_Baru"

kls_jln = arcpy.GetParameterAsText(0)
s_kls_jln = 1

if kls_jln == "Arteri Primer":
    s_kls_jln = 7
elif kls_jln == "Arteri Sekunder":
    s_kls_jln = 6
elif kls_jln == "Kolektor Primer":
    s_kls_jln = 5
elif kls_jln == "Kolektor Sekunder":
    s_kls_jln = 4
elif kls_jln == "Lokal Primer":
    s_kls_jln = 3
elif kls_jln == "Lokal Sekunder":
    s_kls_jln = 2
elif kls_jln == "Lokal Setapak":
    s_kls_jln = 1
else:
    s_kls_jln = 1

persil_fields = [f.name for f in arcpy.ListFields(persil_baru)]

if "kls_jln" not in persil_fields or "s_kls_jln" not in persil_fields:
    arcpy.AddError("Field " + "kls_jln, s_kls_jln" + " tidak ditemukan.")
    raise arcpy.ExecuteError

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(persil_baru).FIDSet)
if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(persil_baru)
    for row in rows:
        row.setValue("kls_jln", kls_jln)
        row.setValue("s_kls_jln", s_kls_jln)
        rows.updateRow(row)
    del row
    del rows

# arcpy.RefreshTOC()
# arcpy.RefreshActiveView()
#edit 28/9/22
arcpy.CalculateField_management(persil_baru, "kls_jln" ,'"'+ kls_jln +'"', "PYTHON3", "")
arcpy.AddMessage("== Proses selesai ==")

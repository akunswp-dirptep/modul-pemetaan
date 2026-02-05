import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

persil_update = "Persil_Taru"

letak = arcpy.GetParameterAsText(0)
s_letak = 1

if letak == "Lain-Lain":
    s_letak = 1
elif letak == "Tusuk Sate":
    s_letak = 2
elif letak == "Normal":
    s_letak = 3
elif letak == "Hook":
    s_letak = 4
fields = [f.name for f in arcpy.ListFields(persil_update)]

if "letak" not in fields or "s_letak" not in fields:
    arcpy.AddError("Field " + "letak, s_letak" + " tidak ditemukan.")
    raise arcpy.ExecuteError

rows = arcpy.UpdateCursor(persil_update)

for row in rows:
    row.setValue("letak", letak)
    row.setValue("s_letak", float(s_letak))
    rows.updateRow(row)

del row
del rows

arcpy.RefreshTOC()
arcpy.RefreshActiveView()

arcpy.AddMessage("== Proses selesai ==")

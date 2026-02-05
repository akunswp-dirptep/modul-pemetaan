import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

persil_taru = "Persil_Taru"

bentuk = arcpy.GetParameterAsText(0)
s_bentuk = 1

if bentuk == "Persegi":
    s_bentuk = 3
elif bentuk == "Tidak beraturan":
    s_bentuk = 1
elif bentuk == "Trapesium":
    s_bentuk = 2

ada_seleksi = len(arcpy.Describe(persil_taru).FIDSet)

if ada_seleksi > 0:
    fields = [f.name for f in arcpy.ListFields(persil_taru)]

    if "bentuk" not in fields or "s_bentuk" not in fields:
        arcpy.AddError("Field " + "bentuk, s_bentuk" + " tidak ditemukan.")
        raise arcpy.ExecuteError

    rows = arcpy.UpdateCursor(persil_taru)

    for row in rows:
        row.setValue("bentuk", bentuk)
        row.setValue("s_bentuk", float(s_bentuk))
        rows.updateRow(row)

    del row
    del rows

    arcpy.RefreshTOC()
    arcpy.RefreshActiveView()

arcpy.AddMessage("== Proses selesai ==")

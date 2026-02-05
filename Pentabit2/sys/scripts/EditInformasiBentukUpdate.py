import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

persil_update = "Persil_Update"

bentuk = arcpy.GetParameterAsText(0)
s_bentuk = 1

if bentuk == "Segi Banyak Tidak Beraturan":
    s_bentuk = 1
elif bentuk == "Segi Tiga":
    s_bentuk = 2
elif bentuk == "Segi Empat Tidak Beraturan":
    s_bentuk = 3
elif bentuk == "Segi Empat Beraturan":
    s_bentuk == 4

fields = [f.name for f in arcpy.ListFields(persil_update)]

if "bentuk" not in fields or "s_bentuk" not in fields:
    arcpy.AddError("Field " + "bentuk, s_bentuk" + " tidak ditemukan.")
    raise arcpy.ExecuteError

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(persil_update).FIDSet)
if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(persil_update)
    for row in rows:
        row.setValue("bentuk", bentuk)
        row.setValue("s_bentuk", float(s_bentuk))
        rows.updateRow(row)

    del row
    del rows

# arcpy.RefreshTOC()
# arcpy.RefreshActiveView()

#edit 28/9/22
arcpy.CalculateField_management(persil_update, "bentuk" ,'"' + bentuk + '"', "PYTHON3", "")
arcpy.AddMessage("== Proses selesai ==")

import arcpy
import os

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

persil_konsolidasi = "Persil_Konsolidasi"
konsolidasi = arcpy.GetParameterAsText(0)

ada_seleksi = len(arcpy.Describe(persil_konsolidasi).FIDSet)

if ada_seleksi > 0:
    sampel_fields = [f.name for f in arcpy.ListFields(persil_konsolidasi)]

    if "obj_konsol" not in sampel_fields:
        arcpy.AddField_management(persil_konsolidasi, "obj_konsol", "TEXT")

    rows = arcpy.UpdateCursor(persil_konsolidasi)

    for row in rows:
        row.setValue("obj_konsol", konsolidasi)
        rows.updateRow(row)

    del row
    del rows

    arcpy.RefreshTOC()
    arcpy.RefreshActiveView()


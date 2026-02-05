import arcpy
import os

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

persil_taru = "Persil_Taru"
taru = arcpy.GetParameterAsText(0)

if taru == 'Taru':
    taru = 'taru'
else:
    taru = 'non taru'

ada_seleksi = len(arcpy.Describe(persil_taru).FIDSet)

if ada_seleksi > 0:
    sampel_fields = [f.name for f in arcpy.ListFields(persil_taru)]

    if "obj_taru" not in sampel_fields:
        arcpy.AddField_management(persil_taru, "obj_taru", "TEXT")

    rows = arcpy.UpdateCursor(persil_taru)

    for row in rows:
        row.setValue("obj_taru", taru)
        rows.updateRow(row)

    del row
    del rows

    arcpy.RefreshTOC()
    arcpy.RefreshActiveView()


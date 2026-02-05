import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

sampel_skor = "Sampel_Skor_Valid"

valid = arcpy.GetParameter(0)

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(sampel_skor).FIDSet)
if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(sampel_skor)
    for row in rows:
        row.status_sam = valid
        rows.updateRow(row)
    del row
    del rows

arcpy.RefreshTOC()
arcpy.RefreshActiveView()

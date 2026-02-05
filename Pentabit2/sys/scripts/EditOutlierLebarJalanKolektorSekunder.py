import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

field = "LebarJalan"
val = float(arcpy.GetParameterAsText(0))

KolektorSekunder = "Outlier_Lebar_Jalan_Kolektor_Sekunder"
JaringanJalan = "JaringanJalan"

rows = arcpy.UpdateCursor(KolektorSekunder)

for row in rows:
    row.setValue(field, val)
    rows.updateRow(row)

del row
del rows

rows = arcpy.UpdateCursor(JaringanJalan)

for row in rows:
    row.setValue(field, val)
    rows.updateRow(row)

del row
del rows

# if arcpy.Exists(persil):
#     arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

arcpy.RefreshTOC()
arcpy.RefreshActiveView()

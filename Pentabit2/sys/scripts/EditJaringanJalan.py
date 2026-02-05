import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

field = arcpy.GetParameterAsText(1)
val = float(arcpy.GetParameterAsText(2))

jaringan_jalan = "Jaringan_Jalan"

rows = arcpy.da.UpdateCursor(jaringan_jalan, [field])
for row in rows:
    #row.setValue(field, val)
    row[0] = val
    rows.updateRow(row)
del row
del rows

# if arcpy.Exists(persil):
#     arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

arcpy.RefreshTOC()
arcpy.RefreshActiveView()

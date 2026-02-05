import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

field = arcpy.GetParameterAsText(1)
val = float(arcpy.GetParameterAsText(2))

sampel_model = "Sampel_Model"
persil_model = "Persil_Model"
prediksi_model = "Sampel_Prediksi"

rows = arcpy.UpdateCursor(sampel_model)

for row in rows:
    row.setValue(field, val)
    rows.updateRow(row)

del row
del rows

rows = arcpy.UpdateCursor(persil_model)

for row in rows:
    row.setValue(field, val)
    rows.updateRow(row)

del row
del rows

rows = arcpy.UpdateCursor(prediksi_model)

for row in rows:
    row.setValue(field, val)
    rows.updateRow(row)

del row
del rows

# if arcpy.Exists(persil):
#     arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

arcpy.RefreshTOC()
arcpy.RefreshActiveView()

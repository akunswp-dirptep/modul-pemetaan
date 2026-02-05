import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

field = arcpy.GetParameterAsText(1)
val = arcpy.GetParameter(2)

sampel_model = "Sampel_Model"
persil_model = "Persil_Model"
prediksi_model = "Sampel_Prediksi"

sampel_fields = [f.name for f in arcpy.ListFields(sampel_model)]
persil_fields = [f.name for f in arcpy.ListFields(persil_model)]
prediksi_fields = [f.name for f in arcpy.ListFields(prediksi_model)]

if field not in sampel_fields or field not in persil_fields or field not in prediksi_fields:
    arcpy.AddError(" ")
    arcpy.AddError(" ")
    arcpy.AddError("FIELD " + field + " TIDAK DITEMUKAN DI SEMUA FEATURE.")
    arcpy.AddError(" ")
    arcpy.AddError(" ")
    raise arcpy.ExecuteError

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(sampel_model).FIDSet)
if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(sampel_model)
    for row in rows:
        if "ln_" + field in sampel_fields:
            row.setValue("ln_" + field, math.log(val))
        if "iv_" + field in sampel_fields and val != 0:
            row.setValue("iv_" + field, 1.0 / val)
        row.setValue(field, val)
        rows.updateRow(row)

    del row
    del rows

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(persil_model).FIDSet)
if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(persil_model)
    for row in rows:
        if "ln_" + field in persil_fields:
            row.setValue("ln_" + field, math.log(val))
        if "iv_" + field in persil_fields and val != 0:
            row.setValue("iv_" + field, 1.0 / val)
        row.setValue(field, val)
        rows.updateRow(row)

    del row
    del rows

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(prediksi_model).FIDSet)
if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(prediksi_model)
    for row in rows:
        if "ln_" + field in prediksi_fields:
            row.setValue("ln_" + field, math.log(val))
        if "iv_" + field in prediksi_fields and val != 0:
            row.setValue("iv_" + field, 1.0 / val)
        row.setValue(field, val)
        rows.updateRow(row)

    del row
    del rows

# if arcpy.Exists(persil):
#     arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

#update 19/10/2021
#arcpy.RefreshTOC()
#arcpy.RefreshActiveView()

import arcpy, os


# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

val = arcpy.GetParameterAsText(0)

status_per = "Indikator_Perubahan_Persil"

sampel_fields = [f.name for f in arcpy.ListFields(status_per)]

if "status_per" not in sampel_fields:
    arcpy.AddError("Field " + "status_per" + " tidak ditemukan.")
    raise arcpy.ExecuteError

rows = arcpy.UpdateCursor(status_per)
for row in rows:
    row.setValue("status_per", val)
    rows.updateRow(row)
del row
del rows

#edit 28/9/22
arcpy.CalculateField_management(status_per, "status_per" ,'"' + val + '"', "PYTHON3", "")

# arcpy.RefreshTOC()
# arcpy.RefreshActiveView()
